FROM python:3.11-slim

WORKDIR /app


RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

#  requirements
COPY requirements.txt .
COPY sim_pitch_models /app/models_data

RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY proto ./proto

#  gRPC 
#RUN python -m grpc_tools.protoc \
#    -I./proto \
#    --python_out=./src \
#    --grpc_python_out=./src \
#    ./proto/prediction.proto


CMD ["python", "-m", "src.main"]
