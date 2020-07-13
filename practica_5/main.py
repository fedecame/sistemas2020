from hardware import *
from so import *
import log


##
##  MAIN 
##
if __name__ == '__main__':
    log.setupLogger()
    log.logger.info('Starting emulator')

    ## setup our hardware and set memory size to 25 "cells"
    HARDWARE.setup(32)

    ## new create the Operative System Kernel
    # "booteamos" el sistema operativo
    kernel = Kernel(printGant = True)

    # kernel.setupScheduler(FCFS())
    # kernel.setupScheduler(PriorityNonPreemptive(3))
    kernel.setupScheduler(PriorityPreemptive(3))
    # kernel.setupScheduler(RoundRobin(3))

    # Ahora vamos a intentar ejecutar 3 programas a la vez
    ##################
    prg1 = Program("prg1.exe", [ASM.IO(), ASM.CPU(2), ASM.CPU(3), ASM.IO(), ASM.CPU(2)])
    prg2 = Program("prg2.exe", [ASM.IO(), ASM.CPU(2)])
    prg3 = Program("prg3.exe", [ASM.IO(), ASM.CPU(4), ASM.IO(), ASM.CPU(1)])

    # prg1 = Program("prg1", [ASM.IO(), ASM.CPU(2), ASM.CPU(2)])
    # prg2 = Program("prg2", [ASM.IO(), ASM.CPU(3)])
    # prg3 = Program("prg3", [ASM.IO(), ASM.CPU(1)])

    # prg1 = Program("prg1", [ASM.CPU(2)])
    # prg2 = Program("prg2", [ASM.CPU(4)])
    # prg3 = Program("prg3", [ASM.CPU(3)])
    
    kernel.fileSystem.write("C:/prg1.exe", prg1)
    kernel.fileSystem.write("C:/prg2.exe", prg2)
    kernel.fileSystem.write("C:/prg3.exe", prg3)

    # execute all programs "concurrently"
    # kernel.run(prg1, 2)
    # kernel.run(prg2, 2)
    # kernel.run(prg3, 1)

    # ejecutamos los programas a partir de un “path” (con una prioridad x)
    kernel.run("C:/prg1.exe", 2)
    kernel.run("C:/prg2.exe", 3)
    kernel.run("C:/prg3.exe", 1)

    ## Switch on computer
    ## Pasamos el switchOn aca abajo, porque teniamos problemas de concurrencia (race conditions) con el Thread del Clock y los profes aconsejaron este workaround
    HARDWARE.switchOn()