# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt from the root directory of the project to the container
COPY ../requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything from the 'app' subdirectory in the local context to the '/app' directory in the container
COPY . /app

# Make port 8443 available to the world outside this container (optional)
EXPOSE 8443


# Run bot.py when the container launches
CMD ["python", "bot.py"]
