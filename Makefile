SHELL := /bin/bash


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

.PHONY: podman-up
up:
	podman-compose down
	podman-compose up -d --build