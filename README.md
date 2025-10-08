# Product-Recommendation-ChaBot

1. **Create a virtuval environment & Activate the virtual environment**
    ```sh
    python3 -m venv <name_of_virtual_env>
    source <name_of_virtual_env>/bin/activate
    ```

2. **Install the requirements**
    ```sh
    pip install -r requirements.txt
    ```

3. **Export / Set environment variables**
    - Make sure your .env file is configured, or export variables manually if needed.

4. **Run the FastAPI app**
    ```sh
    uvicorn main:app
    ```