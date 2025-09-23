# ================================
# ENVIRONMENT VARIABLES
# ================================

GODOT_VERSION ?= 4.5-stable

DOCKER_REGISTRY := ghcr.io
DOCKER_IMAGE_NAME := bdrelling/godot
DOCKER_IMAGE_TAG := $(GODOT_VERSION)
DOCKER_IMAGE := $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG)
DOCKER_IMAGE_FULL := $(DOCKER_REGISTRY)/$(DOCKER_IMAGE)

# ================================
# INFORMATION
# ================================

.PHONY: help info auth-registry build deploy pull clean clean-containers clean-images clean-builder clean-all 

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

info: ## Show image info
	@echo "🤖 Godot Version: $(GODOT_VERSION)"
	@echo "💿 Image: $(DOCKER_IMAGE_FULL)"
	@echo ""
	@echo "🔍 Usage: $$ docker pull $(DOCKER_IMAGE_FULL)"

# ================================
# AUTHENTICATION
# ================================

auth-registry: ## Authenticate with registry (use FORCE_AUTH=true to force re-auth)
	@echo "Checking $(DOCKER_REGISTRY) authentication..."
	@if [ "$(FORCE_AUTH)" = "true" ] || [ ! -f ~/.docker/config.json ] || ! grep -q "$(DOCKER_REGISTRY)" ~/.docker/config.json; then \
		echo "Authenticating with $(DOCKER_REGISTRY).."; \
		echo "$(GITHUB_TOKEN)" | docker login $(DOCKER_REGISTRY) -u $(GITHUB_USERNAME) --password-stdin; \
	else \
		echo "Already authenticated with $(DOCKER_REGISTRY)"; \
	fi

# ================================
# BUILD, PUSH, PULL
# ================================

build: ## Build Godot image for current platform
	@echo "Building Godot $(GODOT_VERSION) image for current platform..."
	docker build --build-arg GODOT_VERSION=$(GODOT_VERSION) -t $(DOCKER_IMAGE_FULL) .

deploy: clean auth-registry ## Build and push multi-arch to registry
	@echo "Building and pushing multi-arch $(DOCKER_IMAGE_FULL) and latest..."
	docker buildx create --use --name godot-builder
	docker buildx build --platform linux/amd64,linux/arm64 \
		--build-arg GODOT_VERSION=$(GODOT_VERSION) \
		-t $(DOCKER_IMAGE_FULL) \
		-t $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME):latest \
		--push .

pull: auth-registry ## Pull Godot image from registry
	@echo "Pulling $(DOCKER_IMAGE_FULL)..."
	docker pull $(DOCKER_IMAGE_FULL)

# ================================
# CLEANUP
# ================================

clean: clean-containers clean-images clean-builder ## Remove all local Godot Docker resources

clean-containers: ## Stop and remove containers using Godot images
	@echo "Stopping and removing containers using Godot images..."
	@docker ps -a --filter "ancestor=$(DOCKER_IMAGE)" --format "{{.ID}}" | xargs -r docker rm -f || true
	@docker ps -a --filter "ancestor=$(DOCKER_IMAGE_FULL)" --format "{{.ID}}" | xargs -r docker rm -f || true
	@docker ps -a --filter "ancestor=$(DOCKER_IMAGE_NAME):latest" --format "{{.ID}}" | xargs -r docker rm -f || true
	@docker ps -a --filter "ancestor=$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME):latest" --format "{{.ID}}" | xargs -r docker rm -f || true
	@echo "Container cleanup complete!"

clean-images: ## Remove Godot images and dangling images
	@echo "Removing Godot images..."
	@docker rmi $(DOCKER_IMAGE) || true
	@docker rmi $(DOCKER_IMAGE_NAME):latest || true
	@docker rmi $(DOCKER_IMAGE_FULL) || true
	@docker rmi $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME):latest || true
	@echo "Removing dangling images (untagged images from failed builds)..."
	@docker image prune -f || true
	@echo "Image cleanup complete!"

clean-builder: ## Remove buildx builder and its cache
	@echo "Removing buildx builder and cache..."
	@docker buildx rm godot-builder || true
	@docker buildx prune -f || true
	@echo "Builder cleanup complete!"

clean-all: ## Remove ALL Docker resources (use with caution!)
	@echo "WARNING: This will remove ALL Docker containers, images, and build cache!"
	@echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
	@sleep 5
	@docker system prune -a -f --volumes || true
	@echo "Full Docker cleanup complete!"
