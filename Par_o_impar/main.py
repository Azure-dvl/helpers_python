def main():
    print('¿En qué número estás pensando?')
    num = int(input())
    
    if num%2!=0:
        print('¡Es un número impar! ¿Puedes añadir otro?')
    elif num%2==0:
        print('Es un número par! ¿Puedes añadir otro?')
    else:
        print('Por favor solo ingrese numeros')

if __name__ == "__main__":
    main()