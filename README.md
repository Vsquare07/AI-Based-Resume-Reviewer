#AI-Based-Resume-Reviewer
##Requirements
- NodeJS(npm)
- Python
- ollama

##Setup
Set the ollama model you wan't to use in `.env` and install it
```sh
ollama pull {your_model}
```

Set your github token in `.env` for increased rate limits.

```sh
#Install dependencies
pip install -r requirements.txt
pip install -r frontend/api/requirements.txt

#Frontend dependencies
cd frontend/web
npm install
```

##Run
```sh
#Start the Ollama service
ollama serve

#Run the local api
uvicorn frontend.api.main:app --reload --port 8000

#Start serving the web page
cd frontend/web
npm run dev
```
