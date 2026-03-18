import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from inference import (
    build_query,
    chat_with_media,
    get_extension,
    invoke_url,
    kSupportedList,
)

app = FastAPI(title="BART Incident Classifier")

@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/submissions")
async def submissions(
    media: list[UploadFile] = File(default=[]),
    description: str = Form(default=None),
):
    submission_id = f"{uuid.uuid4().hex}"
    tmp_paths: list[Path] = []

    try:
        for upload in media:
            ext = get_extension(upload.filename or "")
            if ext not in kSupportedList:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unsupported file type '.{ext}'. "
                    f"Accepted: {', '.join(sorted(kSupportedList))}",
                )

            suffix = f".{ext}"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(await upload.read())
            tmp.close()
            tmp_paths.append(Path(tmp.name))

        query = build_query(description)
        result = chat_with_media(
            invoke_url, [str(p) for p in tmp_paths], query,
            description=description, submission_id=submission_id
        )
        return result

    finally:
        for p in tmp_paths:
            p.unlink(missing_ok=True)
