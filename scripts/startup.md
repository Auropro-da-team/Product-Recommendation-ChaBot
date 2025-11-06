USE " Ctrl+Shift+V " to go into READ-ONLY MODE / PREVIEW

Once you open your project in container use the following commands to start the project 

- Split the terminal or use 2 terminals (You will see a " + " icon on right top of terminal)

- backend:

    ```
    cd backend
    uvicorn main:app --host 0.0.0.0 
    ```

- frontend

    ```
    cd frontend
    npm run dev -- --host
    ```

Make sure you access port with the following ip address and DO NOT use the links displayed after startup in terminal 

    ```
    192.168.1.102:[PORT-NUMBER]
    ```