# Use an official Python runtime as the base image
FROM python:3.11

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask app code into the container
COPY . .

# Expose the port on which your Flask app will run
EXPOSE 5000

# Specify the command to run your Flask app
CMD ["python", "main.py"]
