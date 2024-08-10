''' 
    Nivel principiante
        1. Hola mundo
        2. Suma de dos numeros
        3. Par o impar
        4. Mayor que ...
        5. Tabla multiplicar
        6. Factorial de un numero
        7. Suma de una lista
        8. Mayor de una lista
        9. Verificar si un elemento esta en la lista
        10. Invertir una cadena
'''

def suma(num1:float, num2:float):
    try:
        result=num1+num2
        print(result)
    except:
        print('Solo ingrese numeros')

def par_impar(num:int):
    if num%2!=0:
        print('¡Es un número impar!')
    elif num%2==0:
        print('Es un número par!')
    else:
        print('Por favor solo ingrese numeros')
    print('Compilacion terminada')

def mayoque(num1:float, num2:float):
    if num1>num2:
        print(f'{num1} es mayor')
    elif num1==num2:
        print('Son iguales')
    else:
        print(f'{num2} es mayor')

def tablemultiplicar():
    numlist = [1,2,3,4,5,6,7,8,9,10]
    for num in numlist:
        print(f'Tabla del {num}')
        print(f'{num}*1={num*1}')
        print(f'{num}*2={num*2}')
        print(f'{num}*3={num*3}')
        print(f'{num}*4={num*4}')
        print(f'{num}*5={num*5}')
        print(f'{num}*6={num*6}')
        print(f'{num}*7={num*7}')
        print(f'{num}*8={num*8}')
        print(f'{num}*9={num*9}')
        print(f'{num}*10={num*10}')

def factorial():
    pass

def listsuma():
    pass

def mayorlist():
    pass

def elementinlist():
    pass

def cadenaback():
    pass

def main():
    print('Hola Mundo y bienvenido a mi nivel principiante')

if __name__ == "__main__":
    main()