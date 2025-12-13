IMAGE ?= dcp-docs:latest

.PHONY: build run stop logs

build:
	docker build -t $(IMAGE) .

run:
	docker compose up -d

stop:
	docker compose down

logs:
	docker compose logs -f
