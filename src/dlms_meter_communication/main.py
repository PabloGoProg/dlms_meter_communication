from fastapi import FastAPI

app = FastAPI(
    title="DLMS Meter Communication",
    description="API for DLMS Meter Communication",
    version="0.1.0",
    contact={"name": "PabloGoProg", "email": "pgosorio13@gmail.com"},
)


@app.get("/")
def hello_world():
    return {"message": "Hello World"}
