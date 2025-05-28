from fastapi import FastAPI, Depends,  HTTPException, Header

#Index page
@app.get("/")
async def index():
    return {"message": "Hello World"}
