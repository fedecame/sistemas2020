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

    def __init__(self, id, baseDir, path, priority = None):
        self._id = id
        self._baseDir = baseDir
        self._path = path
        self._estado = NEW_STATE
        self._pc = 0
        self._priority = priority
        self._burstTime = 0 #tiempo que esta en la ready queue

    @property
    def id(self):
        return self._id

    @property
    def baseDir(self):
        return self._baseDir

    @baseDir.setter
    def baseDir(self, baseDir):
        self._baseDir = baseDir

    @property
    def path(self):
        return self._path
    
    @property
    def estado(self):
        return self._estado

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

class SchedulerType():

    def setup(self, readyQueue):
        self._readyQueue = readyQueue
        return self

    def isEmpty(self):
        return self._readyQueue.isEmpty()

    def mustExpropiate(self, pcbInCPU, pcbToAdd):
        return False

class FCFS(SchedulerType):

    def add(self, pcb):
        self._readyQueue.enqueue(pcb)

    def getNext(self):
        return self._readyQueue.dequeue()

class NonPreemptive(SchedulerType):

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

class Preemptive(SchedulerType):

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
        
    def mustExpropiate(self, pcbInCPU, pcbToAdd):
        return pcbToAdd.priority < pcbInCPU.priority

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
        program = irq.parameters[0]
        priority = irq.parameters[1]
        baseDir = self.kernel.loader.load(program)
        pcbId = pcbTable.getNewPID()
        pcb = PCB(pcbId, baseDir, program.name, priority)
        pcbTable.add(pcb)

        scheduler = self.kernel.scheduler
        runningPCB2 = pcbTable.runningPCB
        if (runningPCB2 is None):
            pcb.state = RUNNING_STATE
            pcbTable.runningPCB = pcb
            self.kernel.dispatcher.load(pcb)
        else:
            if (scheduler.mustExpropiate(runningPCB2, pcb)):
                self.kernel.dispatcher.save(runningPCB2)
                runningPCB2.state = READY_STATE
                scheduler.add(runningPCB2)

                print("Expropio, saco el pcb " + str(runningPCB2.id))
                print("Y pongo el pcb " + str(pcb.id))

                pcb.state = RUNNING_STATE
                pcbTable.runningPCB = pcb
                self.kernel.dispatcher.load(pcb)
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

        if (not scheduler.isEmpty()):
            nextPcb = scheduler.getNext()
            nextPcb.state = RUNNING_STATE
            pcbTable.runningPCB = nextPcb
            self.kernel.dispatcher.load(nextPcb)
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
            self.kernel.dispatcher.load(nextPcb)
        else:
            pcbTable.runningPCB = None
        
        log.logger.info(self.kernel.ioDeviceController)


class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcb = self.kernel.ioDeviceController.getFinishedPCB()

        scheduler = self.kernel.scheduler
        pcbTable = self.kernel.pcbTable
        runningPCB2 = pcbTable.runningPCB
        if (runningPCB2 is None):
            pcb.state = RUNNING_STATE
            self.kernel.dispatcher.load(pcb)
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
                self.kernel.dispatcher.load(pcb)
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
            self.kernel.dispatcher.load(pcbToExecute)
            pcbTable.runningPCB = pcbToExecute
            print("Expropio, saco el pcb " + str(runningPCB.id))
            print("Y pongo el pcb " + str(pcbToExecute.id))

class StatsInterruptionHandler(AbstractInterruptionHandler):
    # asumimos que el scheduler es RoundRobin porque solo ese scheduler setea el quantum (activa el Timer)
    def execute(self, irq):
        gantProcesses = self.kernel.gantProcesses

        runningPCB = self.kernel.pcbTable.runningPCB
        # ASUMIENDO que nunca hay instrucciones de IO (como en los ejemplos vistos), cuando no haya un pcb en running es que ya terminaron de ejecutarse todos los pcbs
        if runningPCB is None:
            # _listaDeListas = " cada lista interna representa una fila, osea un proceso "
            _listaDeListas = []
            procesos = set(gantProcesses)
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
                    if (instr == 55):
                        listaARetornar.append(cantidadDeInstrucciones)
                        cantidadDeInstrucciones -= 1
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

            HARDWARE.switchOff()
        else:
            gantProcesses.append(runningPCB.id)

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

# emulates the core of an Operative System
class Kernel():

    def __init__(self, printGant = False):
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

        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)
        self._loader = Loader()
        self._pcbTable = PCBTable()
        self._dispatcher = Dispatcher()
        self._gantProcesses = []

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

    def setupScheduler(self, schedulerType):
        self._scheduler = Scheduler(schedulerType)

    ## emulates a "system call" for programs execution
    def run(self, program, priority = None):
        self.newIRQ = IRQ(NEW_INTERRUPTION_TYPE, [program, priority])
        HARDWARE.interruptVector.handle(self.newIRQ)

        log.logger.info("\n Executing program: {name}".format(name=program.name))
        log.logger.info(HARDWARE)
        

        def __repr__(self):
            return "Kernel "