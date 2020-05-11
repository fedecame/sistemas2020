#!/usr/bin/env python

from hardware import *
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

    def __init__(self, id, baseDir, path):
        self._id = id
        self._baseDir = baseDir
        self._path = path
        self._estado = NEW_STATE
        self._pc = 0

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
        program = irq.parameters
        baseDir = self.kernel.loader.load(program)
        pcbId = pcbTable.getNewPID()
        pcb = PCB(pcbId, baseDir, program.name)
        pcbTable.add(pcb)

        if (pcbTable.runningPCB is None):
            pcb.state = RUNNING_STATE
            pcbTable.runningPCB = pcb
            self.kernel.dispatcher.load(pcb)
        else:
            pcb.state = READY_STATE
            self.kernel.readyQueue.enqueue(pcb)

class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        log.logger.info(" Program Finished ")
        pcbTable = self.kernel.pcbTable
        pcbTerminated = pcbTable.runningPCB
        self.kernel.dispatcher.save(pcbTerminated)
        pcbTerminated.state = TERMINATED_STATE
        pcbTable.remove(pcbTerminated.id)

        readyQueue = self.kernel.readyQueue
        if (not readyQueue.isEmpty()):
            nextPcb = readyQueue.dequeue()
            nextPcb.state = RUNNING_STATE
            pcbTable.runningPCB = nextPcb
            self.kernel.dispatcher.load(nextPcb)

class IoInInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        operation = irq.parameters
        pcb = self.kernel.pcbTable.runningPCB
        self.kernel.dispatcher.save(pcb)
        pcb.state = WAITING_STATE
        self.kernel.ioDeviceController.runOperation(pcb, operation)
        
        pcbTable = self.kernel.pcbTable
        readyQueue = self.kernel.readyQueue
        if (not readyQueue.isEmpty()):
            nextPcb = readyQueue.dequeue()
            nextPcb.state = RUNNING_STATE
            pcbTable.runningPCB = nextPcb
            self.kernel.dispatcher.load(nextPcb)
        else:   
            self.kernel.pcbTable.runningPCB = None     
        
        log.logger.info(self.kernel.ioDeviceController)


class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcb = self.kernel.ioDeviceController.getFinishedPCB()

        readyQueue = self.kernel.readyQueue
        pcbTable = self.kernel.pcbTable
        if (pcbTable.runningPCB is None):
            pcb.state = RUNNING_STATE
            self.kernel.dispatcher.load(pcb)
            pcbTable.runningPCB = pcb
        else:
            pcb.state = READY_STATE
            readyQueue.enqueue(pcb)

        log.logger.info(self.kernel.ioDeviceController)


class Loader():

    def __init__(self):
        self._nextPC = 0

    # loads the program in main memory
    def load(self, program):
        progSize = len(program.instructions)

        self._baseDir = self._nextPC

        self._nextPC = self._baseDir + progSize
        for index in range(self._baseDir, self._nextPC):
            inst = program.instructions[index-self._baseDir]
            HARDWARE.memory.write(index, inst)
        
        return self._baseDir

class Dispatcher():

    def load(self, pcb):
        HARDWARE.cpu.pc = pcb.pc
        HARDWARE.mmu.baseDir = pcb.baseDir

    def save(self, pcb):
        pcb.pc = HARDWARE.cpu.pc
        HARDWARE.cpu.pc = -1


# emulates the core of an Operative System
class Kernel():

    def __init__(self):
        ## setup interruption handlers
        killHandler = KillInterruptionHandler(self)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        ioInHandler = IoInInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)

        newHandler = NewInterruptionHandler(self)
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, newHandler)

        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)
        self._loader = Loader()
        self._pcbTable = PCBTable()
        self._readyQueue = ReadyQueue()
        self._dispatcher = Dispatcher()

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
    def readyQueue(self):
        return self._readyQueue

    @property
    def dispatcher(self):
        return self._dispatcher

    ## emulates a "system call" for programs execution
    def run(self, program):
        self.newIRQ = IRQ(NEW_INTERRUPTION_TYPE, program)
        HARDWARE.interruptVector.handle(self.newIRQ)

        log.logger.info("\n Executing program: {name}".format(name=program.name))
        log.logger.info(HARDWARE)
        

        def __repr__(self):
            return "Kernel "
