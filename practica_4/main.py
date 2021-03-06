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
    HARDWARE.setup(30)

    ## new create the Operative System Kernel
    # "booteamos" el sistema operativo
    kernel = Kernel(printGant = True)

    # kernel.setupScheduler(FCFS())
    # kernel.setupScheduler(PriorityNonPreemptive(3))
    kernel.setupScheduler(PriorityPreemptive(3))
    # kernel.setupScheduler(RoundRobin(3))

    # Ahora vamos a intentar ejecutar 3 programas a la vez
    ##################
    # prg1 = Program("prg1.exe", [ASM.IO(), ASM.CPU(2), ASM.IO(), ASM.CPU(3), ASM.IO(), ASM.CPU(2)])
    # prg2 = Program("prg2.exe", [ASM.IO(), ASM.CPU(7)])
    # prg3 = Program("prg3.exe", [ASM.IO(), ASM.CPU(4), ASM.IO(), ASM.CPU(1)])

    prg1 = Program("prg1.exe", [ASM.IO(), ASM.CPU(2), ASM.CPU(2)])
    prg2 = Program("prg2.exe", [ASM.IO(), ASM.CPU(3)])
    prg3 = Program("prg3.exe", [ASM.IO(), ASM.CPU(1)])

    # prg1 = Program("prg1.exe", [ASM.CPU(2)])
    # prg2 = Program("prg2.exe", [ASM.CPU(4)])
    # prg3 = Program("prg3.exe", [ASM.CPU(3)])

    # execute all programs "concurrently"
    kernel.run(prg1, 2)
    kernel.run(prg2, 2)
    kernel.run(prg3, 1)


    ## Switch on computer
    ## Pasamos el switchOn aca abajo, porque teniamos problemas de concurrencia (race conditions) con el Thread del Clock y los profes aconsejaron este workaround
    HARDWARE.switchOn()