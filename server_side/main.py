import uvicorn
import asyncio
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect

app = FastAPI()
document_content = ""
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    global document_content
    contents = await file.read()
    document_content = contents.decode("utf-8")


    print("File processed and content stored.")
    return {"message": f"Successfully uploaded and processed {file.filename}"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    await websocket.accept()
    global document_content
    try:
        while True:
            # wait for the client to send a question
            question = await websocket.receive_text()

            if not document_content:
                await websocket.send_text("Please upload a context document first.")
                continue
            # Langchain things

            response_message = f"Thinking about your question: {question}..."
            await websocket.send_text(response_message)
            await asyncio.sleep(0.5)

            simulated_stream  = [

            ]

            for chunk in simulated_stream:
                await websocket.send_text(chunk)
                await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        print("Client disconnected")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
