from fastapi import FastAPI, Depends,  HTTPException, Header
app = FastAPI()
#Index page
@app.get("/")
async def index():
    return {"message": "Hello World"}
