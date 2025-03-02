SHELL := /usr/bin/env bash


.PHONY: all
all:
	@echo "Please use one of the following targets:"
	@echo "  make test - run tests (pytest)"


# Run tests with scripts/run_tests.sh
.PHONY: test
test:
	./scripts/run_tests.sh

.PHONY: up
up:
	docker-compose up -d --build

.PHONY: up-dev
up-dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

.PHONY: down
down:
	docker-compose down

.PHONY: podman-up
podman-up:
	podman-compose down
	podman-compose up -d --build
