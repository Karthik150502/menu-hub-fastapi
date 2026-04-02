from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World", "status":200}

@app.get("/test/")
def read_root():
    return {"message": "Testing URL", "status":201}