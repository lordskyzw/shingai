# Use an official Python runtime as the base image
FROM python:3.11.1


WORKDIR /winter


COPY requirements.txt /winter/


RUN pip install -r requirements.txt


COPY . /winter/

ENV MONGO_URI=mongodb://mongo:Szz99GcnyfiKRTms8GbR@containers-us-west-4.railway.app:7055
ENV WHATSAPP_ACCESS_TOKEN=EAAOtcSk30jwBABZC8XRhiYkn0uqX03RBs3Qois85x0VVMNIsHZAVCDnPVkUMIvTdk9TKqwQmZChZBMRG6E5EnuzzsSAGHvfYOncAjWvQN1xwWoYgZBOgaHCZCNPkqnZC9pOHEE4upWnu23UyZCEthiJVih9XQFFmQI65uzE1DCejE6pgXBdYXVGS
ENV PHONE_NUMBER_ID=101879622956347
ENV OPENAI_API_KEY=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
ENV PINECONE_API_KEY=c2b473b8-0500-47c1-9958-c6300567c67b
ENV SERP_API_KEY=8d732beb0ec037938297f3a0abfec80608b5ff26cad5d0cb2e6c2dd1b4855bb0

# Make port 80 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV NAME World

# Run app.py when the container launches
CMD ["python", "main.py"]
