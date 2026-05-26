# app/Dockerfile

FROM python:3.13

WORKDIR /streamlit_app

COPY requirements.txt ./requirements.txt
RUN pip3 install -r requirements.txt

COPY . /streamlit_app

# Expose the port that Streamlit runs on
EXPOSE 8080

# Set the environment variable PORT
ENV PORT 8080

# Start the Streamlit app
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8080"]