''' 
    Nivel principiante
        1. Hola mundo
        2. Suma de dos numeros
        3. Par o impar
        4. Mayor que ...
        5. Tabla multiplicar
        6. Factorial de un numero
        7. Factoria recrusivo
        8. Suma de una lista
        9. Mayor de una lista
        10. Verificar si un elemento esta en la lista
        11. Invertir una cadena
'''

def suma(num1:float, num2:float):
    return num1+num2

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

def factorial(num1:int):
    fact=1
    for i in range(num1+1):
        if i==0:
            i=1
        fact*=i
    return fact

def factotialrecrusivo(num1:int):
    result = 0
    if num1 == 0 or num1 == 1:
        result=1
    elif num1>1:
        result=num1*factotialrecrusivo(num1-1)

    return result

def listsuma():
    numlist = [5,4,7,9,8,6,7]
    sum = 0
    for num in numlist:
        sum+=num
    return sum

def mayorlist():
    numlist = [5,4,7,9,8,6,7]
    x=0
    for num in numlist:
        if x<num:
            x=num
    return x

def elementinlist(x:int):
    numlist = [5,4,7,9,8,6,7]
    for num in numlist:
        if x==num:
            print('Numero encontrado')
            break

def cadenaback():
    numlist = [5,4,7,9,8,6,7]
    numlist.reverse()

    for num in numlist:
        print(num)

def main():
    print('Hola Mundo y bienvenido a mi nivel principiante\nNivel principiante\n2. Suma de dos numeros\n3. Par o impar\n4. Mayor que ...\n5. Tabla multiplicar\n6. Factorial de un numero\n7. Factoria recrusivo\n8. Suma de una lista\n9. Mayor de una lista\n10. Verificar si un elemento esta en la lista\n11. Invertir una cadena')
    num = int(input('Que opcion quieres'))


if __name__ == "__main__":
    main()