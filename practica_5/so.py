#!/usr/bin/env python

from hardware import *
from tabulate import tabulate
import log

#PCB STATES
NEW_STATE = "NEW"
READY_STATE = "READY"
RUNNING_STATE = "RUNNING"
WAITING_STATE = "WAITING"
TERMINATED_STATE = "TERMINATED"


## emulates a compiled program
class Program():

    def __init__(self, name, instructions):
        self._name = name
        self._instructions = self.expand(instructions)

    @property
    def name(self):
        return self._name

    @property
    def instructions(self):
        return self._instructions

    def addInstr(self, instruction):
        self._instructions.append(instruction)

    def expand(self, instructions):
        expanded = []
        for i in instructions:
            if isinstance(i, list):
                ## is a list of instructions
                expanded.extend(i)
            else:
                ## a single instr (a String)
                expanded.append(i)

        ## now test if last instruction is EXIT
        ## if not... add an EXIT as final instruction
        last = expanded[-1]
        if not ASM.isEXIT(last):
            expanded.append(INSTRUCTION_EXIT)

        return expanded

    def __repr__(self):
        return "Program({name}, {instructions})".format(name=self._name, instructions=self._instructions)

class PCB():

    def __init__(self, id, path, priority = None):
        self._id = id
        self._estado = NEW_STATE
        self._pc = 0
        self._path = path
        self._priority = priority
        self._burstTime = 0 #tiempo que esta en la ready queue
        self._limit = 0

    @property
    def id(self):
        return self._id
    
    @property
    def estado(self):
        return self._estado

    @property
    def path(self):
        return self._path

    @estado.setter
    def estado(self, estado):
        self._estado = estado

    @property
    def pc(self):
        return self._pc

    @pc.setter
    def pc(self, pc):
        self._pc = pc

    @property
    def priority(self):
        return self._priority

    @property
    def burstTime(self):
        return self._burstTime

    @burstTime.setter
    def burstTime(self, burstTime):
        self._burstTime = burstTime

    @property
    def limit(self):
        return self._limit

    @limit.setter
    def limit(self, limit):
        self._limit = limit

class PCBTable():
    
    def __init__(self):
        self._pid = 0
        self._pcbs = dict()
        self._runningPCB = None

    def get(self, pid):
        return self._pcbs.get(pid)

    def add(self, pcb):
        self._pcbs[pcb.id] = pcb

    def remove(self, pid):
        return self._pcbs.pop(pid)

    def getNewPID(self):
        self._pid += 1
        return self._pid

    @property
    def runningPCB(self):
        return self._runningPCB

    @runningPCB.setter
    def runningPCB(self, runningPCB):
        self._runningPCB = runningPCB

class Scheduler():

    def __init__(self, schedulerType):
        self._readyQueue = ReadyQueue()
        self._schedulerType = schedulerType.setup(self._readyQueue)

    def add(self, pcb):
        self._schedulerType.add(pcb)

    def getNext(self):
        return self._schedulerType.getNext()

    def isEmpty(self):
        return self._schedulerType.isEmpty() 

    def mustExpropiate(self, pcbInCPU, pcbToAdd):
        return self._schedulerType.mustExpropiate(pcbInCPU, pcbToAdd)

    # definido para imprimir las ready queues del gant
    def getReadyQueueReflection(self):
        return self._schedulerType.getReadyQueueReflection()

class SchedulerType():

    def setup(self, readyQueue):
        self._readyQueue = readyQueue
        return self

    def isEmpty(self):
        return self._readyQueue.isEmpty()

    def mustExpropiate(self, pcbInCPU, pcbToAdd):
        return False

    # definido para imprimir las ready queues del gant
    def getReadyQueueReflection(self):
        return list(self._readyQueue.queue)

class FCFS(SchedulerType):

    def add(self, pcb):
        self._readyQueue.enqueue(pcb)

    def getNext(self):
        return self._readyQueue.dequeue()

class PriorityNonPreemptive(SchedulerType):

    def __init__(self, priorityAmount):
        HARDWARE.clock.addSubscriber(self)
        self._priorityAmount = priorityAmount
        self._readyQueue2 = []
        for n in range(self._priorityAmount):
            self._readyQueue2.append([])

    def add(self, pcb):
        self._readyQueue2[pcb.priority-1].append(pcb)

    def isEmpty(self):
        isEmpty = True
        for ls in self._readyQueue2:
            isEmpty = isEmpty and len(ls) == 0
        return isEmpty
        

    def getNext(self):
        counter = 0
        for ls in self._readyQueue2:
            counter += 1
            if len(ls) > 0:
                return ls.pop(0)
            else:
                print("No ELEMENTS en Prioridad " + str(counter))

    def tick(self, tickNbr):
        for index in range(1, self._priorityAmount):
            for pcb2 in self._readyQueue2[index]:
                pcb2.burstTime += 1
                if pcb2.burstTime >= 3:
                    #reseteo tiempo de espera
                    pcb2.burstTime = 0
                    #swap de lista a una de mayor prioridad
                    #alias "agePcb2"
                    self._readyQueue2[index].remove(pcb2)
                    self._readyQueue2[index-1].append(pcb2)
                    
    # # definido para imprimir las ready queues del gant
    def getReadyQueueReflection(self):
        # aplanar la readyQueue2
        flattened = []
        for ls in self._readyQueue2:
            flattened.extend(ls)

        return flattened

class PriorityPreemptive(PriorityNonPreemptive):

    def mustExpropiate(self, pcbInCPU, pcbToAdd):
        return pcbToAdd.priority < pcbInCPU.priority

class RoundRobin(SchedulerType):

    def __init__(self, quantumValue):
        HARDWARE.timer.quantum = quantumValue

    def add(self, pcb):
        self._readyQueue.enqueue(pcb)

    def getNext(self):
        return self._readyQueue.dequeue()

class ReadyQueue():

    def __init__(self):
        self._queue = []

    def enqueue(self, pcb):
        self._queue.append(pcb)
    
    def dequeue(self):
        return self._queue.pop(0)

    def isEmpty(self):
        return len(self._queue) == 0

    @property
    def queue(self):
        return self._queue

## emulates an Input/Output device controller (driver)
class IoDeviceController():

    def __init__(self, device):
        self._device = device
        self._waiting_queue = []
        self._currentPCB = None

    def runOperation(self, pcb, instruction):
        pair = {'pcb': pcb, 'instruction': instruction}
        # append: adds the element at the end of the queue
        self._waiting_queue.append(pair)
        # try to send the instruction to hardware's device (if is idle)
        self.__load_from_waiting_queue_if_apply()

    def getFinishedPCB(self):
        finishedPCB = self._currentPCB
        self._currentPCB = None
        self.__load_from_waiting_queue_if_apply()
        return finishedPCB

    def __load_from_waiting_queue_if_apply(self):
        if (len(self._waiting_queue) > 0) and self._device.is_idle:
            ## pop(): extracts (deletes and return) the first element in queue
            pair = self._waiting_queue.pop(0)
            #print(pair)
            pcb = pair['pcb']
            instruction = pair['instruction']
            self._currentPCB = pcb
            self._device.execute(instruction)

    # usado para el Gant
    @property
    def currentPCB(self):
        return self._currentPCB

    # usado para el Gant
    @property
    def waitingQueue(self):
        return list(self._waiting_queue)

    def __repr__(self):
        return "IoDeviceController for {deviceID} running: {currentPCB} waiting: {waiting_queue}".format(deviceID=self._device.deviceId, currentPCB=self._currentPCB, waiting_queue=self._waiting_queue)

## emulates the  Interruptions Handlers
class AbstractInterruptionHandler():
    def __init__(self, kernel):
        self._kernel = kernel

    @property
    def kernel(self):
        return self._kernel

    def execute(self, irq):
        log.logger.error("-- EXECUTE MUST BE OVERRIDEN in class {classname}".format(classname=self.__class__.__name__))

class NewInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcbTable = self.kernel.pcbTable
        log.logger.info(" Program started ")
        path = irq.parameters[0]
        priority = irq.parameters[1]
        pcbId = pcbTable.getNewPID()
        pcb = PCB(pcbId, path, priority)
        self.kernel.loader.load(pcb)
        pcbTable.add(pcb)

        scheduler = self.kernel.scheduler
        runningPCB2 = pcbTable.runningPCB
        pageTable = self.kernel.memoryManager.getPageTable(pcb.id)
        if (runningPCB2 is None):
            pcb.state = RUNNING_STATE
            pcbTable.runningPCB = pcb
            self.kernel.dispatcher.load(pcb, pageTable)
        else:
            if (scheduler.mustExpropiate(runningPCB2, pcb)):
                self.kernel.dispatcher.save(runningPCB2)
                runningPCB2.state = READY_STATE
                scheduler.add(runningPCB2)

                print("Expropio, saco el pcb " + str(runningPCB2.id))
                print("Y pongo el pcb " + str(pcb.id))

                pcb.state = RUNNING_STATE
                pcbTable.runningPCB = pcb
                self.kernel.dispatcher.load(pcb, pageTable)
            else:
                pcb.state = READY_STATE
                scheduler.add(pcb)

class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        log.logger.info(" Program Finished ")
        pcbTable = self.kernel.pcbTable
        pcbTerminated = pcbTable.runningPCB
        self.kernel.dispatcher.save(pcbTerminated)
        pcbTerminated.state = TERMINATED_STATE
        pcbTable.remove(pcbTerminated.id)
        scheduler = self.kernel.scheduler
        memoryManager = self.kernel.memoryManager

        # borrar pageTable y liberar los frames correspondientes
        mayBePageTable = memoryManager.deletePagetable(pcbTerminated.id)
        if mayBePageTable is not None:
            memoryManager.freeFrames(mayBePageTable.values())
        
        if (not scheduler.isEmpty()):
            nextPcb = scheduler.getNext()
            nextPcb.state = RUNNING_STATE
            pcbTable.runningPCB = nextPcb
            pageTable = memoryManager.getPageTable(nextPcb.id)
            self.kernel.dispatcher.load(nextPcb, pageTable)
        else:
            pcbTable.runningPCB = None

class IoInInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        operation = irq.parameters[0]
        pcbTable = self.kernel.pcbTable
        pcb = pcbTable.runningPCB
        self.kernel.dispatcher.save(pcb)
        pcb.state = WAITING_STATE
        self.kernel.ioDeviceController.runOperation(pcb, operation)
        scheduler = self.kernel.scheduler

        if (not scheduler.isEmpty()):
            nextPcb = scheduler.getNext()
            nextPcb.state = RUNNING_STATE
            pcbTable.runningPCB = nextPcb
            pageTable = self.kernel.memoryManager.getPageTable(nextPcb.id)
            self.kernel.dispatcher.load(nextPcb, pageTable)
        else:
            pcbTable.runningPCB = None
        
        log.logger.info(self.kernel.ioDeviceController)


class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcb = self.kernel.ioDeviceController.getFinishedPCB()

        scheduler = self.kernel.scheduler
        pcbTable = self.kernel.pcbTable
        runningPCB2 = pcbTable.runningPCB
        pageTable = self.kernel.memoryManager.getPageTable(pcb.id)
        if (runningPCB2 is None):
            pcb.state = RUNNING_STATE
            self.kernel.dispatcher.load(pcb, pageTable)
            pcbTable.runningPCB = pcb
        else:
            # scheduler = self.kernel.scheduler
            if scheduler.mustExpropiate(runningPCB2, pcb):
                self.kernel.dispatcher.save(runningPCB2)
                runningPCB2.state = READY_STATE
                scheduler.add(runningPCB2)

                print("Expropio, saco el pcb " + str(runningPCB2.id))
                print("Y pongo el pcb " + str(pcb.id))

                pcb.state = RUNNING_STATE
                self.kernel.dispatcher.load(pcb, pageTable)
                pcbTable.runningPCB = pcb
            else:
                pcb.state = READY_STATE
                scheduler.add(pcb)

        log.logger.info(self.kernel.ioDeviceController)

class TimeoutInterruptionHandler(AbstractInterruptionHandler):
    # asumimos que el scheduler es RoundRobin porque solo ese scheduler setea el quantum (activa el Timer)
    def execute(self, irq):
        log.logger.info(" Timeout interruption ")
        scheduler = self.kernel.scheduler
        if (scheduler.isEmpty()):
            HARDWARE.timer.reset()
        else:
            pcbTable = self.kernel.pcbTable
            runningPCB = pcbTable.runningPCB
            runningPCB.state = READY_STATE
            self.kernel.dispatcher.save(runningPCB)
            scheduler.add(runningPCB)

            pcbToExecute = scheduler.getNext()
            pcbToExecute.state = RUNNING_STATE
            pageTable = self.kernel.memoryManager.getPageTable(pcbToExecute.id)
            self.kernel.dispatcher.load(pcbToExecute, pageTable)
            pcbTable.runningPCB = pcbToExecute
            print("Expropio, saco el pcb " + str(runningPCB.id))
            print("Y pongo el pcb " + str(pcbToExecute.id))

class StatsInterruptionHandler(AbstractInterruptionHandler):
    # asumimos que el scheduler es RoundRobin porque solo ese scheduler setea el quantum (activa el Timer)
    def execute(self, irq):
        gantProcesses = self.kernel.gantProcesses
        gantReadyQueue = self.kernel.gantReadyQueue
        gantWaitingQueue = self.kernel.gantWaitingQueue

        runningPCB = self.kernel.pcbTable.runningPCB
        ioDeviceController = self.kernel.ioDeviceController
        # ASUMIENDO que nunca hay instrucciones de IO (como en los ejemplos vistos), cuando no haya un pcb en running es que ya terminaron de ejecutarse todos los pcbs
        if (runningPCB is None and ioDeviceController.currentPCB is None): #and 'no hay nadie en waiting queue'
            # _listaDeListas = " cada lista interna representa una fila, osea un proceso "
            _listaDeListas = []
            procesosPrev = set(gantProcesses)

            def retornoSiEsNumero(elem):
                if type(elem) is int:
                    return True
                else:
                    return False
            # filtro y dejo los elementos que son numeros (osea ids de pcbs)
            procesos = list(filter(retornoSiEsNumero, procesosPrev))

            for x in procesos:
                _listaDeListas.append([])
            # aca ya tenemos las listas (vacias) creadas

            def agregaUnTickASublistas(lss, pcbId):
                contador = 0
                for ls in lss:
                    contador += 1
                    if pcbId == contador:
                        ls.append(55)
                    else:
                        ls.append(".")

            for pcbId in gantProcesses:
                agregaUnTickASublistas(_listaDeListas, pcbId)
            # aca ya tengo las listas cargadas con 55s y "."s

            def mapea55sAInstruccionesRestantes(ls):
                cantidadDeInstrucciones = ls.count(55)
                listaARetornar = []
                for instr in ls:
                    if instr == 55:
                        listaARetornar.append(cantidadDeInstrucciones)
                        cantidadDeInstrucciones -= 1
                    elif cantidadDeInstrucciones == 0:
                        listaARetornar.append("")
                    else:
                        listaARetornar.append(".")
                return listaARetornar

            for processList in _listaDeListas:
                indiceDeProcessList = _listaDeListas.index(processList)
                _listaDeListas.remove(processList)
                _listaDeListas.insert(indiceDeProcessList, mapea55sAInstruccionesRestantes(processList))

            listaDeHeaders = list(range(len(gantProcesses)))
            listaDeHeaders.insert(0, "Proceso")

            print(tabulate(_listaDeListas, headers=listaDeHeaders, showindex=list(range(1, len(procesos)+1)), tablefmt="fancy_grid"))
            # aca se imprimio el cuadro de los procesos del Gant

            # ARRANCAMOS A CREAR IMPRESION READY QUEUE GANTT
            def transformaNumeroEnPosicionStr(numero):
                return str(numero)+"°"

            listaDeHeaders.remove("Proceso")
            listaDeHeaders.insert(0, "Ready Q")
            listaDeIndices = list(map(transformaNumeroEnPosicionStr, list(range(1, len(procesos)))))

            readyQueuesImprimible = []
            for x in procesos:
                readyQueuesImprimible.append([])
            readyQueuesImprimible.pop(0)
            # aca ya tenemos las listas (vacias) creadas

            def rellenaEspacios(cantidadDeEspaciosARellenar, listaARellenar):
                cant = cantidadDeEspaciosARellenar
                while cant > 0:
                    listaARellenar[-cant].append("")
                    cant -= 1

            for readyQueue in gantReadyQueue:
                for pcb in readyQueue:
                    readyQueuesImprimible[readyQueue.index(pcb)].append(pcb.id)

                rellenaEspacios(len(readyQueuesImprimible) - len(readyQueue), readyQueuesImprimible)
            #aca ya esta lista para imprimirse la lista
            
            print(tabulate(readyQueuesImprimible, headers=listaDeHeaders, showindex=listaDeIndices, tablefmt="fancy_grid"))

            # ARRANCAMOS A CREAR IMPRESION WAITING QUEUE GANTT
            listaDeHeaders.remove("Ready Q")
            listaDeHeaders.insert(0, "Wait  Q")
            listaDeIndices = list(map(transformaNumeroEnPosicionStr, list(range(1, len(procesos)))))

            waitingQueuesImprimible = []
            for x in procesos:
                waitingQueuesImprimible.append([])
            waitingQueuesImprimible.pop(0)
            # aca ya tenemos las listas (vacias) creadas

            for waitingQueue in gantWaitingQueue:
                for pcb in waitingQueue:
                    waitingQueuesImprimible[waitingQueue.index(pcb)].append(pcb.id)

                rellenaEspacios(len(waitingQueuesImprimible) - len(waitingQueue), waitingQueuesImprimible)
            #aca ya esta lista para imprimirse la lista
            
            print(tabulate(waitingQueuesImprimible, headers=listaDeHeaders, showindex=listaDeIndices, tablefmt="fancy_grid"))

            # ARRANCAMOS A CREAR IMPRESION TOTALES Y PROMEDIOS GANTT

            filasPromediosYTotales = []
            for x in procesos:
                filasPromediosYTotales.append([])
            for x in range(3):
                filasPromediosYTotales.append([])
            # aca ya tenemos las listas (vacias) creadas

            headersPromediosYTotales = ["Proceso", "T. Espera", "T. Retorno"]

            indicesPromediosYTotales = list(range(1, len(procesos)+1))
            indicesPromediosYTotales.extend(["--------", "TOTALES", "PROMEDIO"])

            def aplanarListaDeListas(listaDeListas):
                flattened = []
                for ls in listaDeListas:
                    flattened.extend(ls)
                
                return flattened

            def cuentaAparacionesEnReadyQueue(pcbId):
                readyQueueAplanada = aplanarListaDeListas(readyQueuesImprimible)
                return readyQueueAplanada.count(pcbId)

            def average(ns):
                return round(sum(ns)/len(ns), 2)

            # TIEMPO DE ESPERA
            tiemposDeEspera = []

            for pcbId in procesos:
                tiempoDeEspera = cuentaAparacionesEnReadyQueue(pcbId)
                tiemposDeEspera.append(tiempoDeEspera)
                filasPromediosYTotales[procesos.index(pcbId)].append(tiempoDeEspera)

            def noEsStringVacio(elem):
                if (elem == ""):
                    return False
                else:
                    return True

            def cuentaCeldasNoVaciasEnListaDeProcesosTotales(pcbId):
                return len(list(filter(noEsStringVacio, _listaDeListas[pcbId-1])))

            # TIEMPO DE RETORNO
            tiemposDeRetorno = []

            for pcbId in procesos:
                tiempoDeRetorno = cuentaCeldasNoVaciasEnListaDeProcesosTotales(pcbId)
                tiemposDeRetorno.append(tiempoDeRetorno)
                filasPromediosYTotales[procesos.index(pcbId)].append(tiempoDeRetorno)

            # TOTALES Y PROMEDIOS
            filasPromediosYTotales[len(procesos)].append("---------")
            filasPromediosYTotales[len(procesos)].append("---------")

            # TOTALES
            filasPromediosYTotales[len(procesos)+1].append(sum(tiemposDeEspera))
            filasPromediosYTotales[len(procesos)+1].append(sum(tiemposDeRetorno))

            # PROMEDIOS
            filasPromediosYTotales[len(procesos)+2].append(average(tiemposDeEspera))
            filasPromediosYTotales[len(procesos)+2].append(average(tiemposDeRetorno))

            print(tabulate(filasPromediosYTotales, headers=headersPromediosYTotales, showindex=indicesPromediosYTotales, tablefmt="fancy_grid"))


            # Para el tiempo de espera:
            # recorrer la ready queue y buscar la cantidad de apariciones del pcbId correspondiente.
            # (si hay tiempo, hacer lo mismo para la waiting queue)

            # Para el tiempo de retorno:
            # recorrer la lista del proceso en la _listaDeListas y contar todas las celdas q no estan vacias (osea distintas de "")

            HARDWARE.switchOff()
        else:
            # 3 escenario posibles:
            # 1) hay runningPcb y hay waitingPCB
            # 2) hay runningPcb y NO hay waitingPCB
            # 3) NO hay runningPcb y SI hay waitingPCB

            def agarraPcbDelPair(pairConPcb):
                return pairConPcb['pcb']

            if (runningPCB is not None):
                gantProcesses.append(runningPCB.id)
            else:
                gantProcesses.append("NoEsUnPCBIdValido")
            gantReadyQueue.append(self.kernel.scheduler.getReadyQueueReflection())
            gantWaitingQueue.append(list(map(agarraPcbDelPair, ioDeviceController.waitingQueue)))

class Loader():

    def __init__(self):
        self._nextPC = 0

    # loads the program in main memory
    def load(self, program):
        progSize = len(program.instructions)

        baseDir = self._nextPC

        self._nextPC = baseDir + progSize

        for index in range(0, progSize):
            inst = program.instructions[index]
            HARDWARE.memory.write(index+baseDir, inst)
        
        return baseDir

class Dispatcher():

    def load(self, pcb):
        HARDWARE.cpu.pc = pcb.pc
        HARDWARE.mmu.baseDir = pcb.baseDir
        HARDWARE.timer.reset()

    def save(self, pcb):
        pcb.pc = HARDWARE.cpu.pc
        HARDWARE.cpu.pc = -1

class MemoryManager():

    def __init__(self, frameSize):
        self._framesfree = []
        self._frameSize = frameSize
        self._pageTables = dict()
        self.inicializar(HARDWARE.memory.size // frameSize)

    @property
    def framesFree(self):
        return self._framesfree

    @property
    def frameSize(self):
        return self._frameSize

    @property
    def pageTables(self):
        return self._pageTables

    def inicializar(self, framesAmount):
        # setea la lista de frames (osea ids) con la cantidad correspondiente
        for x in range(framesAmount):
            self._framesfree.append(x)

    def putPageTable(self, pid, pageTable):
        self._pageTables[pid] = pageTable

    def getPageTable(self, pid):
        return self._pageTables[pid]

    def deletePagetable(self, pid):
        return self._pageTables.pop(pid, None)

    def allocFrames(self, n):
        framesOccuppied = []
        if (n > len(self._framesfree)):
            raise Exception("\n* WARNING \n*\n Warning No hay suficiente espacio en memoria para alocar {cantFrames} paginas.".format(cantFrames = n))
        else:
            for m in range(n):
                framesOccuppied.append(self._framesfree.pop())

        return framesOccuppied

    def freeFrames(self, frames):
        self._framesfree.extend(frames)

# emulates the core of an Operative System
class Kernel():

    def __init__(self, printGant = False, frameSize = 4):
        HARDWARE.cpu.enable_stats = printGant

        ## setup interruption handlers
        killHandler = KillInterruptionHandler(self)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        ioInHandler = IoInInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)

        newHandler = NewInterruptionHandler(self)
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, newHandler)

        timeoutHandler = TimeoutInterruptionHandler(self)
        HARDWARE.interruptVector.register(TIMEOUT_INTERRUPTION_TYPE, timeoutHandler)

        statsHandler = StatsInterruptionHandler(self)
        HARDWARE.interruptVector.register(STAT_INTERRUPTION_TYPE, statsHandler)

        HARDWARE.mmu.frameSize = frameSize

        self._fileSystem = FileSystem()
        self._memoryManager = MemoryManager(frameSize)
        self._loader = Loader(frameSize, self._fileSystem, self._memoryManager)
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)
        self._pcbTable = PCBTable()
        self._dispatcher = Dispatcher()
        self._gantProcesses = []
        self._gantReadyQueues = []
        self._gantWaitingQueue = []

    @property
    def ioDeviceController(self):
        return self._ioDeviceController

    @property
    def loader(self):
        return self._loader

    @property
    def pcbTable(self):
        return self._pcbTable

    @property
    def scheduler(self):
        return self._scheduler

    @property
    def dispatcher(self):
        return self._dispatcher

    @property
    def gantProcesses(self):
        return self._gantProcesses

    @property
    def gantReadyQueue(self):
        return self._gantReadyQueues
            
    @property
    def gantWaitingQueue(self):
        return self._gantWaitingQueue

    @property
    def fileSystem(self):
        return self._fileSystem

    @property
    def memoryManager(self):
        return self._memoryManager

    def setupScheduler(self, schedulerType):
        self._scheduler = Scheduler(schedulerType)

    ## emulates a "system call" for programs execution
    def run(self, path, priority = None):
        program = self.fileSystem.read(path)
        self.newIRQ = IRQ(NEW_INTERRUPTION_TYPE, [path, priority])
        HARDWARE.interruptVector.handle(self.newIRQ)

        log.logger.info("\n Executing program: {name}".format(name=program.name))
        log.logger.info(HARDWARE)
        

        def __repr__(self):
            return "Kernel "