# Load environment variables from .env file
ifneq (,$(wildcard .env))
	include .env
endif

DOCKER_USERNAME ?= your-dockerhub-username
IMAGE_NAME := flask-todo-app
IMAGE_TAG := latest
FULL_IMAGE := ${DOCKER_USERNAME}/${IMAGE_NAME}:${IMAGE_TAG}
PORT := 8000

EC2_KEY_PATH ?= /path/to/your/private/key.pem
EC2_USER ?= ubuntu
EC2_IP ?= your-ec2-ip

.PHONY: help build run test push deploy clean

help:
	@echo "Flask Todo App Docker Management"
	@echo ""
	@echo "Available commands:"
	@echo "  make build       - Build the Docker image"
	@echo "  make run         - Run the container locally"
	@echo "  make push        - Push image to Docker Hub"
	@echo "  make deploy      - Deploy to EC2 (run on server)"
	@echo "  make clean       - Remove local containers and images"
	@echo ""

build:
	@echo "Building Docker image..."
	docker build -t ${FULL_IMAGE} .

run:
	@echo "Running container on port ${PORT}..."
	docker run -d -p ${PORT}:${PORT} \
		-e DB_HOST=${DB_HOST} \
		-e DB_USER=${DB_USER} \
		-e DB_PASSWORD=${DB_PASSWORD} \
		-e DB_NAME=${DB_NAME} \
		-e SECRET_KEY=${SECRET_KEY} \
		${FULL_IMAGE}

push:
	@echo "Logging in to Docker Hub..."
	@docker login -u ${DOCKER_USERNAME}
	@echo "Pushing image to Docker Hub..."
	docker push ${FULL_IMAGE}

deploy:
	@echo "Deploying to EC2..."
	ssh -i ${EC2_KEY_PATH} ${EC2_USER}@${EC2_IP} \
		"docker pull ${FULL_IMAGE} && \
		docker stop ${IMAGE_NAME} || true && \
		docker rm ${IMAGE_NAME} || true && \
		docker run -d -p ${PORT}:${PORT} \
			--name ${IMAGE_NAME} \
			-e DB_HOST=${DB_HOST} \
			-e DB_USER=${DB_USER} \
			-e DB_PASSWORD=${DB_PASSWORD} \
			-e DB_NAME=${DB_NAME} \
			-e SECRET_KEY=${SECRET_KEY} \
			${FULL_IMAGE}"

clean:
	@echo "Cleaning up..."
	@docker stop $$(docker ps -aq --filter ancestor=${FULL_IMAGE}) 2>/dev/null || true
	@docker rm $$(docker ps -aq --filter ancestor=${FULL_IMAGE}) 2>/dev/null || true
	@docker rmi ${FULL_IMAGE} 2>/dev/null || true
