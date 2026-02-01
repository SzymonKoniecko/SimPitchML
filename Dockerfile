FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gnupg \
    ca-certificates \
    unixodbc \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Microsoft repo + ODBC Driver 17
RUN curl -sSL -O https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb \
 && dpkg -i packages-microsoft-prod.deb \
 && rm packages-microsoft-prod.deb \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY data_storage /app/data_storage
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


