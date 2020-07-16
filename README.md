| Nombre y Apellido     | Mail                     | usuario Gitlab |
| --------------------- | ------------------------ | -------------- |
| Maximiliano Tarnovski | maxitarnovski@gmail.com  | Tarnomax       |
| Federico Cameriere    | fede.cameriere@gmail.com | fedecame       |

# Practica 1

OK

# Practica 2

OK

# Practica 3

Esta OK excepto por una cosa (lo pueden arreglar directamente en la Practica 4):

- KillInterruptionHandler: si despues de sacar el pcb del CPU no hay nada en la Ready Queue,  kernel.pcbTable.runningPCB queda seteado el ultimo pcb y podria generar problemas. 
- 


# Practica 4

OK ... Muy bueno el Aging y el Gantt!!


Una sola acotacion para pasarlo a la P5: 

- Podrian renombrar las clases de los schedulers de prioridad?? :
  **NonPreemptive**   renombrarlo a: **PriorityNonPreemptive**
  **Preemptive**  renombrarlo a: **PriorityPreemptive**
Porque Preemtive es una caracteristica del Algoritmo (existen varios algoritmos que son Preemptive... pero solo uno que ordena por prioridad y es expropiativo), eso solo un tema de nombres el codigo esta bien


PD: Tambien prodrian haber reutilizado el codigo si  PriorityPreemptive fuese subclase de PriorityNonPreemptive (solo habria que overridear el metodo mustExpropiate())  
    



# Practica 5

OK

