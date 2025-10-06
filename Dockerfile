# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Copy the entire project into the container
COPY . /app/

# Run the initial data setup scripts
RUN python scripts/ingest_data.py && python scripts/init_db.py

# Make the startup script executable
RUN chmod +x ./startup.sh

# Expose the ports for the backend and frontend
EXPOSE 8000
EXPOSE 7860

# The command to run when the container starts
CMD ["./startup.sh"]