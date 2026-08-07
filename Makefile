# Image URL to use all building/pushing image targets
IMAGE_TAG_BASE ?= ghcr.io/llm-d
IMG_TAG ?= latest
IMG ?= $(IMAGE_TAG_BASE)/llm-d-workload-variant-autoscaler:$(IMG_TAG)
KIND_ARGS ?= -t mix -n 3 -g 2   # Default: 3 nodes, 2 GPUs per node, mixed vendors
CLUSTER_GPU_TYPE ?= nvidia-mix
CLUSTER_NODES ?= 3
CLUSTER_GPUS ?= 4
KUBECONFIG ?= $(HOME)/.kube/config
K8S_VERSION ?= v1.32.0

WVA_NS              ?= workload-variant-autoscaler-system
CONTROLLER_NAMESPACE ?= workload-variant-autoscaler-system
MONITORING_NAMESPACE ?= openshift-user-workload-monitoring
LLMD_NAMESPACE       ?= llm-d-optimized-baseline
GATEWAY_NAME         ?= # discovered automatically in e2es
MODEL_ID             ?= e2ewva/dummy-model
DEPLOYMENT           ?= # discovered automatically in e2es
REQUEST_RATE         ?= 20
NUM_PROMPTS          ?= 3000

# E2E test configuration (for test/e2e/ suite)
ENVIRONMENT                 ?= kind-emulator
USE_SIMULATOR               ?= true
SCALE_TO_ZERO_ENABLED       ?= false
DEPLOY_ALERTING_RULES       ?= false
SCALER_BACKEND              ?= keda  # keda (ScaledObject) or none (skip, use pre-installed backend)
LLM_D_ROUTER_VERSION        ?= v0.9.0
GAIE_VERSION                ?= v1.5.0
KV_SPARE_TRIGGER           ?=
QUEUE_SPARE_TRIGGER         ?=
E2E_MONITORING_NAMESPACE    ?= workload-variant-autoscaler-monitoring
E2E_EMULATED_LLMD_NAMESPACE ?= llm-d-sim
E2E_KEDA_NAMESPACE          ?= keda-system
E2E_WVA_SECONDARY_OVERLAY_PATH ?= $(CURDIR)/test/e2e/testdata/secondary-controller
# llm-d-benchmark CLI configuration
# Ensure brew-installed tools (helm >=3.19) take precedence over Rancher Desktop
export PATH := /opt/homebrew/bin:$(PATH)

# Environment-specific benchmark overrides. Copy hack/benchmark/.env.sample ->
# hack/benchmark/.env and fill in. Included BEFORE the ?= defaults below so .env
# values win over them; CLI overrides (make VAR=...) still win over .env. The
# §5.2 image/chart/model/accelerator values have NO ?= default here — they must
# come from .env (or the CLI); benchmark-standup errors if a required one is unset.
-include hack/benchmark/.env
BENCHMARK_REPO_URL   ?= https://github.com/llm-d/llm-d-benchmark.git
BENCHMARK_REPO_DIR   ?= $(CURDIR)/llm-d-benchmark
BENCHMARK_DIRECT_KEDA ?= false
BENCHMARK_REPO_REF   ?= $(if $(filter true,$(BENCHMARK_DIRECT_KEDA)),main,v0.7.0)
# The llm-d-benchmark clone is a checkout of OUR fork: it carries the
# shared-cluster safety patches (presence-gates that stop the standup from
# overwriting cluster-monitoring-config, the istio control plane, the
# thanos-querier ClusterRole, and from installing prometheus-adapter over
# KEDA's metrics APIService) plus, usually, unpushed local work.
# benchmark-standup therefore leaves the clone alone by default -- a blind
# `git reset --hard origin/<ref>` would strip those patches out from under us
# and run the *unguarded* upstream code against a shared cluster.
# Set to true only to deliberately force the clone back to origin, discarding
# local commits and tracked edits.
BENCHMARK_CLONE_FORCE_SYNC ?= false
BENCHMARK_SPEC       ?= $(if $(filter true,$(BENCHMARK_DIRECT_KEDA)),guides/epp-keda-saturation,guides/workload-autoscaling)
BENCHMARK_NAMESPACE  ?= # set via BENCHMARK_NAMESPACE=<namespace>
BENCHMARK_GATEWAY_URL ?= http://infra-llmdbench-inference-gateway-istio.$(BENCHMARK_NAMESPACE).svc.cluster.local:80
BENCHMARK_WORKSPACE  ?= $(CURDIR)
# The harness belongs to the spec of a run, not to this Makefile: it is whatever
# the scenario's harness.name declares. `-l` overrides harness.name inside
# llmdbenchmark, so a hardcoded default here would silently override the scenario.
# Precedence: command line > hack/benchmark/.env > scenario > llmdbenchmark's own
# default (inference-perf).
ifeq ($(origin BENCHMARK_HARNESS),undefined)
BENCHMARK_HARNESS := $(shell python3 $(CURDIR)/hack/benchmark/sync_workloads.py \
	--scenario $(CURDIR)/hack/benchmark/scenarios/$(BENCHMARK_SPEC).yaml \
	--print-harness 2>/dev/null || echo inference-perf)
endif
# Empty by default: the scenario's own harness.experimentProfile is authoritative.
# Set BENCHMARK_WORKLOAD=<name> only to override it on the command line.
BENCHMARK_WORKLOAD   ?=
BENCHMARK_FORCE      ?= true
BENCHMARK_MONITORING ?= true
# Pass --analyze so llmdbenchmark's step_12 runs host-side after the results are
# collected. That step is what writes the Benchmark Report v0.2 YAMLs and applies
# the inference-perf output-token correction (see benchmark-analyze below); it is
# OFF in llmdbenchmark by default, so leaving this false means every
# output-token-derived metric in the reports stays inflated.
BENCHMARK_ANALYZE    ?= true
# Record the images the run ACTUALLY used into its own artifacts. Image pins are
# MINIMUM versions, not exact ones, so drift is flagged and never blocks a run --
# what matters is that the run says what it ran on. Before this existed, only the
# rendered (desired) images were saved, and the WVA controller image -- the whole
# subject of the benchmark -- was recorded nowhere at all.
BENCHMARK_RECORD_IMAGES ?= true
BENCHMARK_UV         ?= false
BENCHMARK_SCENARIOS_DIR ?= $(CURDIR)/test/benchmark/scenarios
# Workload profiles owned by THIS repo, partitioned by harness. The llm-d-benchmark
# clone is cache: profiles are synced into it per run, never authored there.
BENCHMARK_WORKLOADS_DIR ?= $(CURDIR)/hack/benchmark/workloads
BENCHMARK_MODEL_ID   ?= # empty: scenario YAML drives the model; set BENCHMARK_MODEL_ID=<id> to override
# Optional explicit standup step selection (comma-list or ranges, e.g. "0,3,4,5,7,8,9").
# Empty = run all steps (today's behavior). Used to skip cluster-scoped/shared steps
# on shared clusters (see benchmark-standup-shared).
BENCHMARK_STEPS      ?=
BENCHMARK_DECODE_REPLICAS ?= 1
BENCHMARK_KEDA_MIN_REPLICAS ?= 1
BENCHMARK_KEDA_MAX_REPLICAS ?= 10
BENCHMARK_KEDA_SCALE_UP_PERIOD ?= 0
BENCHMARK_KEDA_SCALE_DOWN_PERIOD ?= 300

# Flags for deploy/install.sh (e2e / CI-style cluster infra; no chart VA/HPA).
CREATE_CLUSTER    ?= false
DELETE_CLUSTER    ?= false
DELETE_NAMESPACES ?= false


# Get the currently used golang install path (in GOPATH/bin, unless GOBIN is set)
ifeq (,$(shell go env GOBIN))
GOBIN=$(shell go env GOPATH)/bin
else
GOBIN=$(shell go env GOBIN)
endif

# CONTAINER_TOOL defines the container tool to be used for building images.
# Be aware that the target commands are only tested with Docker which is
# scaffolded by default. However, you might want to replace it to use other
# tools. (i.e. podman)
CONTAINER_TOOL ?= docker

# Setting SHELL to bash allows bash commands to be executed by recipes.
# Options are set to exit when a recipe line exits non-zero or a piped command fails.
SHELL = /usr/bin/env bash -o pipefail
.SHELLFLAGS = -ec

.PHONY: all
all: build

##@ General

# The help target prints out all targets with their descriptions organized
# beneath their categories. The categories are represented by '##@' and the
# target descriptions by '##'. The awk command is responsible for reading the
# entire set of makefiles included in this invocation, looking for lines of the
# file as xyz: ## something, and then pretty-format the target and help. Then,
# if there's a line with ##@ something, that gets pretty-printed as a category.
# More info on the usage of ANSI control characters for terminal formatting:
# https://en.wikipedia.org/wiki/ANSI_escape_code#SGR_parameters
# More info on the awk command:
# http://linuxcommand.org/lc3_adv_awk.php

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

.PHONY: manifests
manifests: controller-gen ## Generate WebhookConfiguration and ClusterRole objects.
	$(CONTROLLER_GEN) rbac:roleName=manager-role webhook paths="./..." \
		output:rbac:artifacts:config=config/base/rbac
	# controller-gen writes `role.yaml`; rename to match the
	# (<app>-)?<kind>.yaml convention used under config/.
	mv config/base/rbac/role.yaml config/base/rbac/manager-clusterrole.yaml

.PHONY: generate
generate: controller-gen ## Generate code containing DeepCopy, DeepCopyInto, and DeepCopyObject method implementations.
	$(CONTROLLER_GEN) object:headerFile="hack/boilerplate.go.txt" paths="./..."

.PHONY: fmt
fmt: ## Run go fmt against code.
	go fmt ./...

.PHONY: vet
vet: ## Run go vet against code.
	go vet ./...

.PHONY: test
test: manifests generate fmt vet setup-envtest helm ## Run tests.
	KUBEBUILDER_ASSETS="$(shell $(ENVTEST) use $(ENVTEST_K8S_VERSION) --bin-dir $(LOCALBIN) -p path)" PATH="$(LOCALBIN):$(PATH)" go test $$(go list ./... | grep -v /e2e | grep -v /benchmark) -coverprofile cover.out

# Creates a multi-node Kind cluster
# Adds emulated GPU labels and capacities per node
.PHONY: create-kind-cluster
create-kind-cluster:
	export KIND=$(KIND) KUBECTL=$(KUBECTL) && \
		deploy/kind-emulator/setup.sh -t $(CLUSTER_GPU_TYPE) -n $(CLUSTER_NODES) -g $(CLUSTER_GPUS)

# Destroys the Kind cluster created by `create-kind-cluster`
.PHONY: destroy-kind-cluster
destroy-kind-cluster:
	export KIND=$(KIND) KUBECTL=$(KUBECTL) && \
        deploy/kind-emulator/teardown.sh


## Deploy WVA to OpenShift cluster with specified image.
.PHONY: deploy-wva-on-openshift
deploy-wva-on-openshift: manifests kustomize ## Deploy WVA to OpenShift cluster with specified image.
	@echo "Deploying WVA to OpenShift with image: $(IMG)"
	@echo "Target namespace: $(WVA_NS)"
	WVA_NS=$(WVA_NS) IMG=$(IMG) ENVIRONMENT=openshift ./deploy/install.sh

## Undeploy WVA from OpenShift.
.PHONY: undeploy-wva-on-openshift
undeploy-wva-on-openshift:
	@echo ">>> Undeploying workload-variant-autoscaler from OpenShift"
	export KIND=$(KIND) KUBECTL=$(KUBECTL) ENVIRONMENT=openshift WVA_NS=$(WVA_NS) && \
		deploy/install.sh --undeploy

## Deploy WVA on Kubernetes with the specified image.
.PHONY: deploy-wva-on-k8s
deploy-wva-on-k8s: manifests kustomize ## Deploy WVA on Kubernetes with the specified image.
	@echo "Deploying WVA on Kubernetes with image: $(IMG)"
	@echo "Target namespace: $(WVA_NS)"
	WVA_NS=$(WVA_NS) IMG=$(IMG) ENVIRONMENT=kubernetes ./deploy/install.sh

## Undeploy WVA from Kubernetes.
.PHONY: undeploy-wva-on-k8s
undeploy-wva-on-k8s:
	@echo ">>> Undeploying workload-variant-autoscaler from Kubernetes"
	export KIND=$(KIND) KUBECTL=$(KUBECTL) ENVIRONMENT=kubernetes WVA_NS=$(WVA_NS) && \
		deploy/install.sh --undeploy

# E2E tests on Kind cluster for saturation-based autoscaling
# The default setup assumes Kind is pre-installed and builds/loads the Manager Docker image locally.
# Supports FOCUS and SKIP variables for ginkgo test filtering.
# Setup options:
# - CERT_MANAGER_INSTALL_SKIP=true: Skip certManager installation during test setup.
# - IMAGE_BUILD_SKIP=true: Skip building the WVA docker image during test setup.
# - INFRA_SETUP_SKIP=true: Skip setting up the llm-d and the WVA controller manager during test setup. Reload the docker image if necessary.
# - INFRA_TEARDOWN_SKIP=true: Skip tearing down the Kind cluster during test teardown.

# Consolidated e2e test targets (environment-agnostic)
# These targets use the test/e2e/ suite that works on any Kubernetes cluster
# Supports FOCUS and SKIP variables for ginkgo test filtering.

# Deploys WVA + monitoring + scaler (install.sh), then EPP (install-epp.sh). No model server or VA/HPA.
# Works for all environments: kind-emulator (default), openshift, kubernetes.
# For OpenShift/Kubernetes: ENVIRONMENT=openshift LLMD_NS=<your-ns> make deploy-e2e-infra
# If IMG is set, builds the image locally first (unless SKIP_BUILD=true).
.PHONY: deploy-e2e-infra
deploy-e2e-infra: ## Deploy e2e test infrastructure (WVA + EPP; no model server or VA/HPA). Works for kind-emulator, openshift, kubernetes.
	@echo "Deploying e2e test infrastructure..."
	@if [ -n "$(IMG)" ]; then \
		echo "IMG is set to '$(IMG)'"; \
		if [ "$(SKIP_BUILD)" != "true" ]; then \
			echo "Building local image (SKIP_BUILD not set)..."; \
			$(MAKE) docker-build IMG=$(IMG); \
		else \
			echo "Skipping image build (SKIP_BUILD=true) - assuming image already exists"; \
		fi; \
		echo "Extracting image repo and tag from IMG..."; \
		if echo "$(IMG)" | grep -q ":"; then \
			IMAGE_REPO=$$(echo $(IMG) | cut -d: -f1); \
			IMAGE_TAG=$$(echo $(IMG) | cut -d: -f2); \
		else \
			IMAGE_REPO="$(IMG)"; \
			IMAGE_TAG="latest"; \
		fi; \
		echo "Using local image: $$IMAGE_REPO:$$IMAGE_TAG"; \
		ENVIRONMENT=$(ENVIRONMENT) \
		SCALER_BACKEND=$(SCALER_BACKEND) \
		ENABLE_SCALE_TO_ZERO=$(SCALE_TO_ZERO_ENABLED) \
		DEPLOY_ALERTING_RULES=$(DEPLOY_ALERTING_RULES) \
		WVA_IMAGE_REPO=$$IMAGE_REPO \
		WVA_IMAGE_TAG=$$IMAGE_TAG \
		WVA_IMAGE_PULL_POLICY=IfNotPresent \
		./deploy/install.sh; \
	else \
		echo "IMG not set - using default image from registry (latest)"; \
		ENVIRONMENT=$(ENVIRONMENT) \
		SCALER_BACKEND=$(SCALER_BACKEND) \
		ENABLE_SCALE_TO_ZERO=$(SCALE_TO_ZERO_ENABLED) \
		DEPLOY_ALERTING_RULES=$(DEPLOY_ALERTING_RULES) \
		./deploy/install.sh; \
	fi
	@ENVIRONMENT=$(ENVIRONMENT) \
		LLM_D_ROUTER_VERSION=$(LLM_D_ROUTER_VERSION) \
		GAIE_VERSION=$(GAIE_VERSION) \
		LLMD_NS=$${LLMD_NS:-$(E2E_EMULATED_LLMD_NAMESPACE)} \
		WVA_PROJECT=$(CURDIR) \
		ENABLE_SCALE_TO_ZERO=$(SCALE_TO_ZERO_ENABLED) \
		./deploy/install-epp.sh
	@NS=$${WVA_NS:-workload-variant-autoscaler-system}; \
	if [ -n "$(KV_SPARE_TRIGGER)" ] || [ -n "$(QUEUE_SPARE_TRIGGER)" ]; then \
		echo "Applying optional WVA capacity threshold overrides (KV_SPARE_TRIGGER / QUEUE_SPARE_TRIGGER)..."; \
		$(KUBECTL) patch configmap wva-saturation-scaling-config \
			-n "$$NS" --type=merge \
			-p "{\"data\":{\"default\":\"kvSpareTrigger: $(KV_SPARE_TRIGGER)\\nqueueSpareTrigger: $(QUEUE_SPARE_TRIGGER)\\n\"}}"; \
	fi


# Runs the smoke subset of the e2e suite. KEDA is the only scaler backend.
.PHONY: test-e2e-smoke
test-e2e-smoke: ## Run smoke e2e tests
	@echo "Running smoke e2e tests..."
	$(eval FOCUS_ARGS := $(if $(FOCUS),-ginkgo.focus="$(FOCUS)",))
	$(eval SKIP_ARGS := $(if $(SKIP),-ginkgo.skip="$(SKIP)",))
	KUBECONFIG=$(KUBECONFIG) \
	ENVIRONMENT=$(ENVIRONMENT) \
	WVA_NAMESPACE=$(CONTROLLER_NAMESPACE) \
	LLMD_NAMESPACE=$(E2E_EMULATED_LLMD_NAMESPACE) \
	MONITORING_NAMESPACE=$(E2E_MONITORING_NAMESPACE) \
	WVA_E2E_SECONDARY_OVERLAY_PATH=$${WVA_E2E_SECONDARY_OVERLAY_PATH:-$(E2E_WVA_SECONDARY_OVERLAY_PATH)} \
	USE_SIMULATOR=$(USE_SIMULATOR) \
	SCALE_TO_ZERO_ENABLED=$(SCALE_TO_ZERO_ENABLED) \
	DEPLOY_ALERTING_RULES=$(DEPLOY_ALERTING_RULES) \
	SCALER_BACKEND=keda \
	MODEL_ID=$(MODEL_ID) \
	go test ./test/e2e/ -timeout 35m -v -ginkgo.v \
		-ginkgo.label-filter="smoke" $(FOCUS_ARGS) $(SKIP_ARGS); \
	TEST_EXIT_CODE=$$?; \
	echo ""; \
	echo "=========================================="; \
	echo "Test execution completed. Exit code: $$TEST_EXIT_CODE"; \
	echo "=========================================="; \
	exit $$TEST_EXIT_CODE

# Runs the complete e2e test suite (KEDA backend, excluding smoke and flaky tests).
.PHONY: test-e2e-full
test-e2e-full: ## Run full e2e test suite
	@echo "Running full e2e test suite..."
	$(eval FOCUS_ARGS := $(if $(FOCUS),-ginkgo.focus="$(FOCUS)",))
	$(eval SKIP_ARGS := $(if $(SKIP),-ginkgo.skip="$(SKIP)",))
	KUBECONFIG=$(KUBECONFIG) \
	ENVIRONMENT=$(ENVIRONMENT) \
	WVA_NAMESPACE=$(CONTROLLER_NAMESPACE) \
	WVA_E2E_SECONDARY_OVERLAY_PATH=$${WVA_E2E_SECONDARY_OVERLAY_PATH:-$(E2E_WVA_SECONDARY_OVERLAY_PATH)} \
	USE_SIMULATOR=$(USE_SIMULATOR) \
	SCALE_TO_ZERO_ENABLED=$(SCALE_TO_ZERO_ENABLED) \
	DEPLOY_ALERTING_RULES=$(DEPLOY_ALERTING_RULES) \
	SCALER_BACKEND=keda \
	KEDA_NAMESPACE=$(E2E_KEDA_NAMESPACE) \
	MODEL_ID=$(MODEL_ID) \
	go test ./test/e2e/ -timeout 35m -v -ginkgo.v \
		-ginkgo.label-filter="full && !smoke && !flaky" $(FOCUS_ARGS) $(SKIP_ARGS); \
	TEST_EXIT_CODE=$$?; \
	echo ""; \
	echo "=========================================="; \
	echo "Test execution completed. Exit code: $$TEST_EXIT_CODE"; \
	echo "=========================================="; \
	exit $$TEST_EXIT_CODE

# Convenience targets for local e2e testing

# Convenience target that deploys KEDA infra + runs smoke tests.
# Set DELETE_CLUSTER=true to delete Kind cluster after tests (default: keep cluster for debugging).
.PHONY: test-e2e-smoke-with-setup
test-e2e-smoke-with-setup:
	$(MAKE) deploy-e2e-infra DEPLOY_ALERTING_RULES=true SCALER_BACKEND=keda
	$(MAKE) test-e2e-smoke DEPLOY_ALERTING_RULES=true

# Runs only the multi-controller (dual namespace-scoped) e2e tests.
.PHONY: test-e2e-multi-controller
test-e2e-multi-controller: ## Run multi-controller e2e tests
	@echo "Running multi-controller e2e tests..."
	$(eval FOCUS_ARGS := $(if $(FOCUS),-ginkgo.focus="$(FOCUS)",))
	$(eval SKIP_ARGS := $(if $(SKIP),-ginkgo.skip="$(SKIP)",))
	KUBECONFIG=$(KUBECONFIG) \
	ENVIRONMENT=$(ENVIRONMENT) \
	WVA_NAMESPACE=$(CONTROLLER_NAMESPACE) \
	LLMD_NAMESPACE=$(E2E_EMULATED_LLMD_NAMESPACE) \
	MONITORING_NAMESPACE=$(E2E_MONITORING_NAMESPACE) \
	WVA_E2E_SECONDARY_OVERLAY_PATH=$${WVA_E2E_SECONDARY_OVERLAY_PATH:-$(E2E_WVA_SECONDARY_OVERLAY_PATH)} \
	USE_SIMULATOR=$(USE_SIMULATOR) \
	SCALE_TO_ZERO_ENABLED=$(SCALE_TO_ZERO_ENABLED) \
	DEPLOY_ALERTING_RULES=$(DEPLOY_ALERTING_RULES) \
	SCALER_BACKEND=$(SCALER_BACKEND) \
	MODEL_ID=$(MODEL_ID) \
	go test ./test/e2e/ -timeout 35m -v -ginkgo.v \
		-ginkgo.label-filter="multi-controller" $(FOCUS_ARGS) $(SKIP_ARGS); \
	TEST_EXIT_CODE=$$?; \
	echo ""; \
	echo "=========================================="; \
	echo "Test execution completed. Exit code: $$TEST_EXIT_CODE"; \
	echo "=========================================="; \
	exit $$TEST_EXIT_CODE

# Convenience target that deploys infra + runs multi-controller tests.
.PHONY: test-e2e-multi-controller-with-setup
test-e2e-multi-controller-with-setup: deploy-e2e-infra test-e2e-multi-controller

# Convenience target that deploys KEDA infra + runs full test suite.
# Set DELETE_CLUSTER=true to delete Kind cluster after tests (default: keep cluster for debugging).
# LWS is installed because the full suite includes LeaderWorkerSet scale-from-zero tests.
.PHONY: test-e2e-full-with-setup
test-e2e-full-with-setup:
	DEPLOY_LWS=true SCALER_BACKEND=keda $(MAKE) deploy-e2e-infra
	$(MAKE) test-e2e-full


##@ llm-d-benchmark CLI (standup / run / teardown)

# llmdbenchmark binary from the benchmark repo venv
BENCHMARK_VENV       = $(BENCHMARK_REPO_DIR)/.venv
LLMDBENCHMARK        = $(shell command -v llmdbenchmark 2>/dev/null || echo $(BENCHMARK_VENV)/bin/llmdbenchmark)
# Interpreter for the local plotting helpers. The benchmark venv carries the
# plotting deps (matplotlib); the system python3 usually does not, which made
# benchmark-plot-two-variant fail with ModuleNotFoundError. Prefer the venv,
# fall back to python3 so the target still runs outside a prepared workspace.
PLOT_PYTHON          ?= $(shell [ -x $(BENCHMARK_VENV)/bin/python ] && echo $(BENCHMARK_VENV)/bin/python || echo python3)

# Common llmdbenchmark flags (spec + workspace + base dir for config resolution)
BENCHMARK_CLI_FLAGS = --spec $(BENCHMARK_SPEC) --workspace $(BENCHMARK_WORKSPACE) --base-dir $(BENCHMARK_REPO_DIR)

.PHONY: benchmark-install
benchmark-install: ## Clone llm-d-benchmark at BENCHMARK_REPO_REF (default v0.7.0) and install the llmdbenchmark CLI
	@if [ ! -d "$(BENCHMARK_REPO_DIR)" ]; then \
		echo "Cloning llm-d-benchmark @ $(BENCHMARK_REPO_REF)..."; \
		git clone --branch $(BENCHMARK_REPO_REF) $(BENCHMARK_REPO_URL) $(BENCHMARK_REPO_DIR); \
	else \
		echo "llm-d-benchmark already cloned at $(BENCHMARK_REPO_DIR); checking out $(BENCHMARK_REPO_REF)..."; \
		cd $(BENCHMARK_REPO_DIR) && git fetch --tags && git checkout $(BENCHMARK_REPO_REF); \
	fi
	@cd $(BENCHMARK_REPO_DIR) && ./install.sh $(if $(filter true,$(BENCHMARK_UV)),--uv,--no-uv)
	@echo "Upgrading helm-diff to v3.15.10 for Helm 4 compatibility..."
	@helm plugin uninstall diff 2>/dev/null || true
	@helm plugin install https://github.com/databus23/helm-diff --version v3.15.10 --verify=false 2>&1

.PHONY: benchmark-standup
benchmark-standup: ## Stand up the benchmark environment (set BENCHMARK_NAMESPACE=<namespace>, MODEL_ID=<model>; BENCHMARK_DIRECT_KEDA=true for controller-free EPP+KEDA autoscaling instead of WVA)
	@if [ -z "$(BENCHMARK_NAMESPACE)" ]; then \
		echo "ERROR: BENCHMARK_NAMESPACE is required. Usage: make benchmark-standup BENCHMARK_NAMESPACE=<namespace>"; \
		exit 1; \
	fi
	@if [ "$(BENCHMARK_DIRECT_KEDA)" = "true" ]; then \
		echo "Direct-KEDA mode: this feature isn't in a released llm-d-benchmark tag yet — upgrading the llm-d-benchmark checkout to '$(BENCHMARK_REPO_REF)' (unreleased)..."; \
		if ! kubectl get crd scaledobjects.keda.sh -n $(BENCHMARK_NAMESPACE) >/dev/null 2>&1; then \
			echo "ERROR: KEDA is not installed on this cluster (scaledobjects.keda.sh CRD not found)."; \
			echo "Install KEDA first (e.g. 'make deploy-e2e-infra SCALER_BACKEND=keda ENVIRONMENT=$(ENVIRONMENT)', or your platform's KEDA operator) and re-run."; \
			exit 1; \
		fi; \
		echo "KEDA ScaledObject CRD found — proceeding with direct-KEDA standup (no WVA controller)."; \
	fi
	@# CLONE SAFETY. Upstream's standup forces the llm-d-benchmark clone back to
	@# origin: `git checkout -- config/{scenarios,specification,templates}` plus
	@# `git reset --hard origin/<ref>`. For us that clone is a checkout of OUR
	@# FORK -- it carries the shared-cluster safety patches (skip the
	@# cluster-monitoring-config overwrite, presence-gate the cluster-scoped
	@# gateway/RBAC applies) and usually some unpushed local work. A blind reset
	@# therefore does two bad things at once: it destroys local commits, and it
	@# can silently run the standup with the shared-cluster guards missing.
	@# Default is now: never rewrite the clone -- report its state and continue.
	@# Opt in to the old destructive behaviour with BENCHMARK_CLONE_FORCE_SYNC=true.
	@if [ -d "$(BENCHMARK_REPO_DIR)/.git" ]; then \
		cd $(BENCHMARK_REPO_DIR) || exit 1; \
		branch=$$(git rev-parse --abbrev-ref HEAD 2>/dev/null); \
		if [ "$$branch" != "$(BENCHMARK_REPO_REF)" ]; then \
			echo "ERROR: llm-d-benchmark clone is on '$$branch' but BENCHMARK_REPO_REF=$(BENCHMARK_REPO_REF)."; \
			echo "Refusing to switch branches automatically -- that would change which code runs against the cluster."; \
			echo "Check out the intended branch yourself, or set BENCHMARK_REPO_REF=$$branch."; \
			exit 1; \
		fi; \
		if [ "$(BENCHMARK_CLONE_FORCE_SYNC)" = "true" ]; then \
			echo "BENCHMARK_CLONE_FORCE_SYNC=true -- forcing clone to origin/$(BENCHMARK_REPO_REF); local commits and tracked edits WILL be discarded."; \
			git fetch --tags origin || exit 1; \
			git reset --hard origin/$(BENCHMARK_REPO_REF) || exit 1; \
		else \
			git fetch --tags origin >/dev/null 2>&1 || echo "  (warning: git fetch failed; using the local clone as-is)"; \
			ahead=$$(git rev-list --count origin/$(BENCHMARK_REPO_REF)..HEAD 2>/dev/null || echo "?"); \
			behind=$$(git rev-list --count HEAD..origin/$(BENCHMARK_REPO_REF) 2>/dev/null || echo "?"); \
			dirty=$$(git status --porcelain | wc -l); \
			echo "llm-d-benchmark clone: branch $$branch @ $$(git rev-parse --short HEAD) -- left untouched"; \
			echo "  vs origin/$(BENCHMARK_REPO_REF): ahead $$ahead, behind $$behind; working tree: $$dirty modified/untracked path(s)"; \
			echo "  (set BENCHMARK_CLONE_FORCE_SYNC=true to force-sync to origin instead)"; \
			[ "$$ahead" = "0" ] || echo "  NOTE: $$ahead local commit(s) are not on origin -- push them so this run is reproducible."; \
		fi; \
	fi
	@missing=""; \
	for t in helm kubectl oc helmfile yq kustomize jq crane skopeo; do \
		command -v $$t >/dev/null 2>&1 || missing="$$missing $$t"; \
	done; \
	[ -x "$(LLMDBENCHMARK)" ] || missing="$$missing llmdbenchmark"; \
	[ -d "$(BENCHMARK_REPO_DIR)/.git" ] || missing="$$missing llm-d-benchmark-clone"; \
	if [ -z "$$missing" ]; then \
		echo "All benchmark dependencies present -- skipping benchmark-install (its install.sh runs 'sudo apt-get update' on Ubuntu, which must not run hidden in a non-interactive shell)."; \
	else \
		echo "ERROR: benchmark dependencies missing:$$missing"; \
		echo "These are installed by install.sh using 'sudo' -- it must NOT be run hidden in a background/non-interactive shell."; \
		echo "Run it yourself in a terminal (it will prompt for your sudo password), then re-run this target:"; \
		echo "    make benchmark-install BENCHMARK_REPO_REF=$(BENCHMARK_REPO_REF)"; \
		exit 1; \
	fi
	@# (the upstream `git reset --hard origin/$(BENCHMARK_REPO_REF)` that used to
	@# live here is now handled by the CLONE SAFETY block above, and only runs
	@# when BENCHMARK_CLONE_FORCE_SYNC=true)
	@if [ -f "$(CURDIR)/hack/benchmark/scenarios/$(BENCHMARK_SPEC).yaml" ]; then \
		echo "Copying local scenario: hack/benchmark/scenarios/$(BENCHMARK_SPEC).yaml -> $(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml"; \
		mkdir -p "$(BENCHMARK_REPO_DIR)/config/scenarios/$$(dirname $(BENCHMARK_SPEC))"; \
		cp "$(CURDIR)/hack/benchmark/scenarios/$(BENCHMARK_SPEC).yaml" \
		   "$(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml"; \
	fi
	@if [ -f "$(CURDIR)/hack/benchmark/scenarios/$(BENCHMARK_SPEC).yaml.j2" ]; then \
		echo "Copying local specification: hack/benchmark/scenarios/$(BENCHMARK_SPEC).yaml.j2 -> $(BENCHMARK_REPO_DIR)/config/specification/$(BENCHMARK_SPEC).yaml.j2"; \
		mkdir -p "$(BENCHMARK_REPO_DIR)/config/specification/$$(dirname $(BENCHMARK_SPEC))"; \
		cp "$(CURDIR)/hack/benchmark/scenarios/$(BENCHMARK_SPEC).yaml.j2" \
		   "$(BENCHMARK_REPO_DIR)/config/specification/$(BENCHMARK_SPEC).yaml.j2"; \
	fi
	@# The standup skips installing prometheus-adapter when this ClusterRole looks
	@# helm-owned. Stubbing it is therefore what keeps the install (and its claim on
	@# the cluster-wide external.metrics APIService that KEDA owns) from happening.
	@# But the object is cluster-scoped and shared, so: never overwrite it. If it is
	@# already ours, do nothing at all. If it is helm-owned by some other release,
	@# stop -- re-annotating would hijack ownership of another tenant's object.
	@# Only create it when genuinely absent, and let any failure abort the standup:
	@# a swallowed error here would leave us believing the gate will fire when it
	@# will not, which is the fail-dangerous direction.
	@if [ "$(BENCHMARK_SKIP_PROMETHEUS_ADAPTER)" = "true" ]; then \
		cr=prometheus-adapter-resource-reader; \
		own_ns=$$(kubectl get clusterrole $$cr -n $(BENCHMARK_NAMESPACE) --ignore-not-found \
			-o jsonpath='{.metadata.annotations.meta\.helm\.sh/release-namespace}' 2>/dev/null); \
		if [ -n "$$own_ns" ] && [ "$$own_ns" != "$(WVA_MONITORING_NAMESPACE)" ]; then \
			echo "ERROR: clusterrole/$$cr is helm-owned by release-namespace '$$own_ns', not '$(WVA_MONITORING_NAMESPACE)'."; \
			echo "Refusing to re-annotate it: that would hijack helm ownership of a cluster-scoped object"; \
			echo "belonging to another tenant's prometheus-adapter release. Investigate before proceeding."; \
			exit 1; \
		elif [ -n "$$own_ns" ]; then \
			echo "clusterrole/$$cr already stubbed for $(WVA_MONITORING_NAMESPACE) -- leaving it untouched."; \
		else \
			echo "Stubbing clusterrole/$$cr so standup's existing-PA probe passes (cluster-scoped CREATE)..."; \
			kubectl create clusterrole $$cr -n $(BENCHMARK_NAMESPACE) \
				--verb=get,list,watch --resource=pods,nodes || exit 1; \
			kubectl annotate clusterrole $$cr -n $(BENCHMARK_NAMESPACE) \
				meta.helm.sh/release-name=prometheus-adapter \
				meta.helm.sh/release-namespace=$(WVA_MONITORING_NAMESPACE) || exit 1; \
			kubectl label clusterrole $$cr -n $(BENCHMARK_NAMESPACE) \
				app.kubernetes.io/managed-by=Helm || exit 1; \
		fi; \
	fi
	@echo "Injecting PYTORCH_ALLOC_CONF, decode replicas, and KEDA config into scenario YAML ($(BENCHMARK_SPEC).yaml)..."
	@sed -i.bak 's/extraEnvVars: \[\]/extraEnvVars:\n        - name: PYTORCH_ALLOC_CONF\n          value: "expandable_segments:True"/' \
		$(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml
	@sed -i.bak 's/replicas: 2$$/replicas: $(BENCHMARK_DECODE_REPLICAS)/' \
		$(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml
	@awk ' \
		/scaledObject:/ { in_keda=1 } \
		in_keda && /^    [a-z]/ && !/scaledObject:/ { in_keda=0 } \
		in_keda && /minReplicas: / { gsub(/minReplicas: [0-9]+/, "minReplicas: $(BENCHMARK_KEDA_MIN_REPLICAS)"); } \
		in_keda && /maxReplicas: / { gsub(/maxReplicas: [0-9]+/, "maxReplicas: $(BENCHMARK_KEDA_MAX_REPLICAS)"); } \
		in_keda && /scaleUp:/ { scale_section="up"; } \
		in_keda && /scaleDown:/ { scale_section="down"; } \
		in_keda && scale_section=="up" && /periodSeconds: 180/ { gsub(/periodSeconds: 180/, "periodSeconds: $(BENCHMARK_KEDA_SCALE_UP_PERIOD)"); scale_section=""; } \
		in_keda && scale_section=="down" && /periodSeconds: 300/ { gsub(/periodSeconds: 300/, "periodSeconds: $(BENCHMARK_KEDA_SCALE_DOWN_PERIOD)"); scale_section=""; } \
		{ print } \
	' $(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml > $(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml.tmp && \
	mv $(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml.tmp $(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml
	@echo "Substituting .env image/chart/model/workdir tokens into scenario ($(BENCHMARK_SPEC).yaml)..."
	@sed -i.tokbak \
		-e 's|__WVA_IMAGE_REPO__|$(WVA_IMAGE_REPO)|g' \
		-e 's|__WVA_IMAGE_TAG__|$(WVA_IMAGE_TAG)|g' \
		-e 's|__VLLM_IMAGE_REPO__|$(VLLM_IMAGE_REPO)|g' \
		-e 's|__VLLM_IMAGE_TAG__|$(VLLM_IMAGE_TAG)|g' \
		-e 's|__HARNESS_IMAGE_REPO__|$(HARNESS_IMAGE_REPO)|g' \
		-e 's|__HARNESS_IMAGE_TAG__|$(HARNESS_IMAGE_TAG)|g' \
		-e 's|__WVA_CHART_VERSION__|$(WVA_CHART_VERSION)|g' \
		-e 's|__PROMETHEUS_ADAPTER_CHART_VERSION__|$(PROMETHEUS_ADAPTER_CHART_VERSION)|g' \
		-e 's|__BENCHMARK_MODEL_ID__|$(BENCHMARK_MODEL_ID)|g' \
		-e 's|__BENCHMARK_MODEL_SHORTNAME__|$(BENCHMARK_MODEL_SHORTNAME)|g' \
		-e 's|__PROM_RELEASE__|$(PROM_RELEASE_LABEL)|g' \
		-e 's|__WVA_WORKDIR__|$(WVA_WORKDIR)|g' \
		$(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml
	@rm -f $(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml.tokbak
	@if grep -qE '__[A-Z_]+__' $(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml; then \
		echo "ERROR: unsubstituted placeholders remain in $(BENCHMARK_SPEC).yaml — set them in hack/benchmark/.env (see .env.sample):"; \
		grep -oE '__[A-Z_]+__' $(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml | sort -u | sed 's/^/  /'; \
		exit 1; \
	fi
	$(LLMDBENCHMARK) $(BENCHMARK_CLI_FLAGS) standup \
		-p $(BENCHMARK_NAMESPACE) \
		$(if $(BENCHMARK_MODEL_ID),-m $(BENCHMARK_MODEL_ID),) \
		$(if $(BENCHMARK_STEPS),--step $(BENCHMARK_STEPS),) \
		$(if $(filter true,$(BENCHMARK_MONITORING)),--monitoring,); \
	rc=$$?; \
	mv $(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml.bak \
	   $(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml; \
	if [ $$rc -eq 0 ] && [ "$(BENCHMARK_MONITORING)" = "true" ]; then \
		echo "Enabling user-workload monitoring for namespace $(BENCHMARK_NAMESPACE)..."; \
		oc label namespace $(BENCHMARK_NAMESPACE) openshift.io/user-workload-monitoring=enabled --overwrite 2>/dev/null && \
		echo "✅ Monitoring label applied. Prometheus will begin scraping ServiceMonitors in this namespace."; \
	fi; \
	exit $$rc

.PHONY: benchmark-preflight
benchmark-preflight: ## Read-only shared-cluster pre-flight: assert every fork safety gate will hold (set BENCHMARK_NAMESPACE=<namespace>)
	@if [ -z "$(BENCHMARK_NAMESPACE)" ]; then \
		echo "ERROR: BENCHMARK_NAMESPACE is required. Usage: make benchmark-preflight BENCHMARK_NAMESPACE=<namespace>"; \
		exit 1; \
	fi
	@python3 $(CURDIR)/hack/benchmark/preflight_shared_cluster.py \
		-n $(BENCHMARK_NAMESPACE) \
		--repo-dir $(BENCHMARK_REPO_DIR) \
		--expect-ref $(BENCHMARK_REPO_REF)

.PHONY: benchmark-standup-shared
benchmark-standup-shared: ## Shared-cluster-safe standup: pre-flight gate, then steps 0,3,4,5,7,8,9 (skips only step_02 admin CRDs/SCCs); requires BENCHMARK_NAMESPACE
	@if [ -z "$(BENCHMARK_NAMESPACE)" ]; then \
		echo "ERROR: BENCHMARK_NAMESPACE is required. Usage: make benchmark-standup-shared BENCHMARK_NAMESPACE=<namespace>"; \
		exit 1; \
	fi
	@# GATE. Our fork skips every cluster-scoped operation the upstream standup
	@# would perform, but each skip is a *presence* gate -- it fires because the
	@# shared object already exists. Absence reads as "not installed yet, go
	@# install it", so a deleted precondition silently converts a safe standup
	@# into a destructive one (worst case: a real prometheus-adapter install
	@# claiming the cluster-wide external.metrics APIService that KEDA owns).
	@# Assert the preconditions BEFORE touching anything, and refuse to start if
	@# any is missing. Read-only; fails the whole target on any gating failure.
	@$(MAKE) benchmark-preflight BENCHMARK_NAMESPACE=$(BENCHMARK_NAMESPACE)
	@echo "Shared-cluster standup: steps 0,3,4,5,7,8,9 (skipping only 02 admin-prereqs)."
	@$(MAKE) benchmark-standup BENCHMARK_STEPS=0,3,4,5,7,8,9 BENCHMARK_NAMESPACE=$(BENCHMARK_NAMESPACE)

.PHONY: benchmark-run
benchmark-run: ## Run a single benchmark workload (set BENCHMARK_NAMESPACE=<namespace>, MODEL_ID=<model>, BENCHMARK_HARNESS=guidellm|inference-perf)
	@if [ -z "$(BENCHMARK_NAMESPACE)" ]; then \
		echo "ERROR: BENCHMARK_NAMESPACE is required. Usage: make benchmark-run BENCHMARK_NAMESPACE=<namespace>"; \
		exit 1; \
	fi
	@mkdir -p "$(BENCHMARK_SCENARIOS_DIR)"
	@if [ -n "$(BENCHMARK_WORKLOAD)" ] && [ "$(BENCHMARK_DIRECT_KEDA)" = "true" ] && [ -f "$(BENCHMARK_SCENARIOS_DIR)/$(BENCHMARK_WORKLOAD)" ]; then \
		echo "Injecting external model endpoint for direct-KEDA mode..."; \
		sed -i.bak 's|base_url: .*|base_url: http://infra-llmdbench-inference-gateway.$(BENCHMARK_NAMESPACE).svc.cluster.local:80|' \
			"$(BENCHMARK_SCENARIOS_DIR)/$(BENCHMARK_WORKLOAD)"; \
		rm -f "$(BENCHMARK_SCENARIOS_DIR)/$(BENCHMARK_WORKLOAD).bak"; \
	fi
	@# Fetch workload from inference-perf catalog if not found locally and harness is inference-perf
	@if [ -n "$(BENCHMARK_WORKLOAD)" ] && [ "$(BENCHMARK_HARNESS)" = "inference-perf" ] && [ ! -f "$(BENCHMARK_SCENARIOS_DIR)/$(BENCHMARK_WORKLOAD)" ] && [ ! -f "$(BENCHMARK_SCENARIOS_DIR)/$(BENCHMARK_WORKLOAD).in" ]; then \
		echo "Fetching $(BENCHMARK_WORKLOAD) from inference-perf workload-catalog..."; \
		if curl -sfL "https://raw.githubusercontent.com/kubernetes-sigs/inference-perf/main/workload-catalog/$(BENCHMARK_WORKLOAD)/inference-perf.yaml" \
			-o "$(BENCHMARK_SCENARIOS_DIR)/$(BENCHMARK_WORKLOAD)"; then \
			echo "Successfully fetched $(BENCHMARK_WORKLOAD)"; \
		else \
			echo "ERROR: Could not fetch $(BENCHMARK_WORKLOAD) from inference-perf workload-catalog"; \
			echo "Available workloads: interactive-chat, code-generation, deep-research, reasoning, batch-summarization-rag, batch-synthetic-data-generation"; \
			exit 1; \
		fi; \
	fi
	@if [ -f "$(CURDIR)/hack/benchmark/scenarios/$(BENCHMARK_SPEC).yaml" ]; then \
		echo "Copying local scenario: hack/benchmark/scenarios/$(BENCHMARK_SPEC).yaml -> $(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml"; \
		mkdir -p "$(BENCHMARK_REPO_DIR)/config/scenarios/$$(dirname $(BENCHMARK_SPEC))"; \
		cp "$(CURDIR)/hack/benchmark/scenarios/$(BENCHMARK_SPEC).yaml" \
		   "$(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml"; \
	fi
	@if [ -f "$(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml" ]; then \
		echo "Substituting .env image/chart/model/workdir tokens into scenario ($(BENCHMARK_SPEC).yaml)..."; \
		sed -i.tokbak \
			-e 's|__WVA_IMAGE_REPO__|$(WVA_IMAGE_REPO)|g' \
			-e 's|__WVA_IMAGE_TAG__|$(WVA_IMAGE_TAG)|g' \
			-e 's|__VLLM_IMAGE_REPO__|$(VLLM_IMAGE_REPO)|g' \
			-e 's|__VLLM_IMAGE_TAG__|$(VLLM_IMAGE_TAG)|g' \
			-e 's|__HARNESS_IMAGE_REPO__|$(HARNESS_IMAGE_REPO)|g' \
			-e 's|__HARNESS_IMAGE_TAG__|$(HARNESS_IMAGE_TAG)|g' \
			-e 's|__WVA_CHART_VERSION__|$(WVA_CHART_VERSION)|g' \
			-e 's|__PROMETHEUS_ADAPTER_CHART_VERSION__|$(PROMETHEUS_ADAPTER_CHART_VERSION)|g' \
			-e 's|__BENCHMARK_MODEL_ID__|$(BENCHMARK_MODEL_ID)|g' \
			-e 's|__BENCHMARK_MODEL_SHORTNAME__|$(BENCHMARK_MODEL_SHORTNAME)|g' \
			-e 's|__PROM_RELEASE__|$(PROM_RELEASE_LABEL)|g' \
			-e 's|__WVA_WORKDIR__|$(WVA_WORKDIR)|g' \
			"$(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml"; \
		rm -f "$(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml.tokbak"; \
		if grep -qE '__[A-Z_]+__' "$(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml"; then \
			echo "ERROR: unsubstituted placeholders remain in $(BENCHMARK_SPEC).yaml — set them in hack/benchmark/.env (see .env.sample):"; \
			grep -oE '__[A-Z_]+__' "$(BENCHMARK_REPO_DIR)/config/scenarios/$(BENCHMARK_SPEC).yaml" | sort -u | sed 's/^/  /'; \
			exit 1; \
		fi; \
	fi
	@if [ -f "$(CURDIR)/hack/benchmark/scenarios/$(BENCHMARK_SPEC).yaml.j2" ]; then \
		echo "Copying local specification: hack/benchmark/scenarios/$(BENCHMARK_SPEC).yaml.j2 -> $(BENCHMARK_REPO_DIR)/config/specification/$(BENCHMARK_SPEC).yaml.j2"; \
		mkdir -p "$(BENCHMARK_REPO_DIR)/config/specification/$$(dirname $(BENCHMARK_SPEC))"; \
		cp "$(CURDIR)/hack/benchmark/scenarios/$(BENCHMARK_SPEC).yaml.j2" \
		   "$(BENCHMARK_REPO_DIR)/config/specification/$(BENCHMARK_SPEC).yaml.j2"; \
	fi
	@# Workload profiles live in THIS repo (source of truth), not in the clone
	@# (cache). The scenario selects one by name via harness.experimentProfile, so
	@# sync the whole harness directory and let the scenario pick -- then assert the
	@# named profile is actually reproducible, not a hand-placed clone leftover.
	@python3 $(CURDIR)/hack/benchmark/sync_workloads.py \
		--scenario $(CURDIR)/hack/benchmark/scenarios/$(BENCHMARK_SPEC).yaml \
		--workloads-dir $(BENCHMARK_WORKLOADS_DIR) \
		--repo-dir $(BENCHMARK_REPO_DIR) \
		--harness $(BENCHMARK_HARNESS)
	@if [ -f "$(BENCHMARK_SCENARIOS_DIR)/$(BENCHMARK_WORKLOAD).in" ]; then \
		cp "$(BENCHMARK_SCENARIOS_DIR)/$(BENCHMARK_WORKLOAD).in" \
		   "$(BENCHMARK_REPO_DIR)/workload/profiles/$(BENCHMARK_HARNESS)/$(BENCHMARK_WORKLOAD).in"; \
		cp "$(BENCHMARK_SCENARIOS_DIR)/$(BENCHMARK_WORKLOAD).in" \
		   "$(BENCHMARK_REPO_DIR)/workload/profiles/$(BENCHMARK_HARNESS)/$(BENCHMARK_WORKLOAD)"; \
	elif [ -f "$(BENCHMARK_SCENARIOS_DIR)/$(BENCHMARK_WORKLOAD)" ]; then \
		echo "Copying local workload from $(BENCHMARK_SCENARIOS_DIR)/$(BENCHMARK_WORKLOAD) to harness..."; \
		cp "$(BENCHMARK_SCENARIOS_DIR)/$(BENCHMARK_WORKLOAD)" \
		   "$(BENCHMARK_REPO_DIR)/workload/profiles/$(BENCHMARK_HARNESS)/$(BENCHMARK_WORKLOAD).yaml"; \
		if [ -n "$(BENCHMARK_MODEL_ID)" ]; then \
			echo "Injecting MODEL_ID=$(BENCHMARK_MODEL_ID) into workload profile..."; \
			sed -i.bak 's|model_name: .*|model_name: $(BENCHMARK_MODEL_ID)|' \
				"$(BENCHMARK_REPO_DIR)/workload/profiles/$(BENCHMARK_HARNESS)/$(BENCHMARK_WORKLOAD).yaml"; \
			rm -f "$(BENCHMARK_REPO_DIR)/workload/profiles/$(BENCHMARK_HARNESS)/$(BENCHMARK_WORKLOAD).yaml.bak"; \
		fi; \
	fi
	@# Observe the stack BEFORE load is applied -- that is the honest answer to
	@# "what did this run run on", and it does not depend on pods surviving the
	@# run (the harness pod is deleted, decode scales back down). Staged to a temp
	@# file because llmdbenchmark has not created the run directory yet; filed into
	@# it once the run completes. Reports drift, never blocks: pins are minimums.
	@if [ "$(BENCHMARK_RECORD_IMAGES)" = "true" ]; then \
		python3 $(CURDIR)/hack/benchmark/record_images.py \
			-n $(BENCHMARK_NAMESPACE) \
			--wva-image "$(WVA_IMAGE_REPO):$(WVA_IMAGE_TAG)" \
			--vllm-image "$(VLLM_IMAGE_REPO):$(VLLM_IMAGE_TAG)" \
			--harness-image "$(HARNESS_IMAGE_REPO):$(HARNESS_IMAGE_TAG)" \
			--out "$(BENCHMARK_WORKSPACE)/.images-pending.yaml"; \
	fi
	$(LLMDBENCHMARK) $(BENCHMARK_CLI_FLAGS) run \
		-p $(BENCHMARK_NAMESPACE) \
		-l $(BENCHMARK_HARNESS) \
		$(if $(BENCHMARK_WORKLOAD),-w $(BENCHMARK_WORKLOAD).yaml,) \
		$(if $(BENCHMARK_MODEL_ID),-m $(BENCHMARK_MODEL_ID),) \
		$(if $(filter true,$(BENCHMARK_MONITORING)),--monitoring,) \
		$(if $(filter true,$(BENCHMARK_ANALYZE)),--analyze,) \
		--wait-timeout $(BENCHMARK_WAIT_TIMEOUT)
	@# File the pre-run image record into the run llmdbenchmark just created. Never
	@# fatal: the run itself succeeded, and losing the report step over bookkeeping
	@# would be the worse outcome.
	@if [ -f "$(BENCHMARK_WORKSPACE)/.images-pending.yaml" ]; then \
		RUN_DIR=$$(ls -td $(BENCHMARK_WORKSPACE)/$${USER}-*/ 2>/dev/null | head -1); \
		if [ -z "$$RUN_DIR" ]; then \
			echo "WARNING: could not locate the run directory; image record left at"; \
			echo "         $(BENCHMARK_WORKSPACE)/.images-pending.yaml"; \
		elif [ -f "$$RUN_DIR/environment/images.yaml" ]; then \
			echo "WARNING: $$RUN_DIR already has an image record — this run created no"; \
			echo "         directory of its own (a dry run?). Refusing to overwrite an"; \
			echo "         earlier run's record; left at .images-pending.yaml."; \
		else \
			mkdir -p "$$RUN_DIR/environment" && \
			mv "$(BENCHMARK_WORKSPACE)/.images-pending.yaml" \
			   "$$RUN_DIR/environment/images.yaml" && \
			echo "Recorded actual images: $$RUN_DIR/environment/images.yaml"; \
		fi; \
	fi
	@echo ""
	@echo "========================================="
	@echo "  Generating benchmark report..."
	@echo "========================================="
	@$(MAKE) benchmark-report
	@$(MAKE) benchmark-plot-two-variant || true

.PHONY: benchmark-report
benchmark-report: ## Generate a markdown table from the latest benchmark results
	@LATEST_DIR=$$(ls -td $(BENCHMARK_WORKSPACE)/$${USER}-*/results/$(BENCHMARK_HARNESS)-*_* 2>/dev/null | head -1); \
	if [ -z "$$LATEST_DIR" ]; then \
		echo "ERROR: No benchmark results found in $(BENCHMARK_WORKSPACE)"; \
		exit 1; \
	fi; \
	echo "Results directory: $$LATEST_DIR"; \
	echo ""; \
	if [ -n "$(BENCHMARK_TWO_VARIANT_SECONDARY_SUFFIX)" ]; then \
		python3 $(CURDIR)/hack/benchmark/postprocess.py \
			--secondary-suffix $(BENCHMARK_TWO_VARIANT_SECONDARY_SUFFIX) \
			--scenario-yaml $(CURDIR)/hack/benchmark/scenarios/$(BENCHMARK_SPEC).yaml \
			--variant-config $(VARIANT_CONFIG) \
			$$LATEST_DIR; \
	else \
		python3 $(CURDIR)/hack/benchmark/postprocess.py $$LATEST_DIR; \
	fi

.PHONY: benchmark-record-images
benchmark-record-images: ## Show the images the stack is actually running vs the .env pins (read-only)
	@# Standalone check: run this before a benchmark to see what the stack is on.
	@# Pins are MINIMUM versions, so a newer image is reported as fine. Always
	@# exits 0 -- it flags drift, it does not gate.
	@python3 $(CURDIR)/hack/benchmark/record_images.py \
		-n $(BENCHMARK_NAMESPACE) \
		--wva-image "$(WVA_IMAGE_REPO):$(WVA_IMAGE_TAG)" \
		--vllm-image "$(VLLM_IMAGE_REPO):$(VLLM_IMAGE_TAG)" \
		--harness-image "$(HARNESS_IMAGE_REPO):$(HARNESS_IMAGE_TAG)"

.PHONY: benchmark-analyze
benchmark-analyze: ## Apply the inference-perf output-token correction to the latest results (idempotent)
	@# Standalone path for results collected before BENCHMARK_ANALYZE existed, or
	@# when a run's analysis step was skipped. inference-perf derives output_len by
	@# re-tokenizing generated text, which inflates it (1.77x on the 2026-08-03
	@# staircase) along with every output-token-derived metric. The correction
	@# rescales the v0.2 reports from the server's own completion_tokens; it stamps
	@# an annotation and skips reports already corrected, so re-running is free.
	@LATEST_DIR=$$(ls -td $(BENCHMARK_WORKSPACE)/$${USER}-*/results/$(BENCHMARK_HARNESS)-*_* 2>/dev/null | head -1); \
	if [ -z "$$LATEST_DIR" ]; then \
		echo "ERROR: No benchmark results found in $(BENCHMARK_WORKSPACE)"; \
		exit 1; \
	fi; \
	echo "Results directory: $$LATEST_DIR"; \
	$(BENCHMARK_VENV)/bin/python -c 'import sys; from llmdbenchmark.analysis.output_token_correction import correct_inference_perf_output_tokens as c; e = c(sys.argv[1]); print("output-token correction: " + (e if e else "applied or already present"))' "$$LATEST_DIR"

BENCHMARK_TWO_VARIANT_SECONDARY_SUFFIX ?= v2

.PHONY: benchmark-plot-two-variant
benchmark-plot-two-variant: ## Plot two-variant replica/latency/throughput graph from the latest results (no-op for single-variant runs)
	@LATEST_DIR=$$(ls -td $(BENCHMARK_WORKSPACE)/$${USER}-*/results/$(BENCHMARK_HARNESS)-*_* 2>/dev/null | head -1); \
	if [ -z "$$LATEST_DIR" ]; then \
		echo "No benchmark results found, skipping two-variant plot"; \
		exit 0; \
	fi; \
	$(PLOT_PYTHON) $(CURDIR)/hack/benchmark/plot_two_variant_pipeline.py \
		$$LATEST_DIR && \
	echo "Two-variant plot: $$LATEST_DIR/metrics/graphs/two_variant_v2_full_pipeline.png"

VARIANT_CONFIG ?= $(CURDIR)/hack/benchmark/scenarios/guides/variants/v2-tp1-cheaper.yaml
# Prometheus URL for KEDA ScaledObject triggers. Default is the OCP thanos-querier.
# Override for vanilla Kubernetes clusters, e.g.:
#   PROMETHEUS_URL=http://prometheus.monitoring.svc.cluster.local:9090
PROMETHEUS_URL ?= https://thanos-querier.openshift-monitoring.svc.cluster.local:9091
WVA_V2_SATURATION_CONFIGMAP ?= $(CURDIR)/hack/benchmark/scenarios/wva_threshold/wva_saturation_v2_config.yaml
WVA_CONTROLLER_DEPLOY ?= deploy/workload-variant-autoscaler-controller-manager
WVA_ROLLOUT_TIMEOUT ?= 120s
WVA_MONITORING_NAMESPACE ?= workload-variant-autoscaler-monitoring

.PHONY: benchmark-configure-variants
benchmark-configure-variants: ## Configure the WVA variant set from one YAML (set BENCHMARK_NAMESPACE=<namespace>, optional VARIANT_CONFIG=<path>, PROMETHEUS_URL=<url>)
	@if [ -z "$(BENCHMARK_NAMESPACE)" ]; then \
		echo "ERROR: BENCHMARK_NAMESPACE is required. Usage: make benchmark-configure-variants BENCHMARK_NAMESPACE=<namespace>"; \
		exit 1; \
	fi
	@if [ -z "$(ACCELERATOR_NAME)" ]; then \
		echo "ERROR: required benchmark .env value ACCELERATOR_NAME unset (see hack/benchmark/.env.sample)"; \
		exit 1; \
	fi
	python3 $(CURDIR)/hack/benchmark/configure_variants.py \
		-n $(BENCHMARK_NAMESPACE) \
		--config $(VARIANT_CONFIG) \
		--prometheus-url $(PROMETHEUS_URL) \
		--accelerator-name $(ACCELERATOR_NAME)

.PHONY: benchmark-add-variant
benchmark-add-variant: benchmark-configure-variants ## Deprecated alias for benchmark-configure-variants (cost/min/max now live in VARIANT_CONFIG)

.PHONY: benchmark-enable-v2-saturation
benchmark-enable-v2-saturation: ## Enable WVA saturation V2 analyzer (apply configmap + restart controller)
	@if [ -z "$(BENCHMARK_NAMESPACE)" ]; then \
		echo "ERROR: BENCHMARK_NAMESPACE is required. Usage: make benchmark-enable-v2-saturation BENCHMARK_NAMESPACE=<namespace>"; \
		exit 1; \
	fi
	@# Detect the saturation ConfigMap name: Kustomize installs use wva-saturation-scaling-config,
	@# Helm-based installs use workload-variant-autoscaler-wva-saturation-scaling-config.
	@# Prefer the shorter Kustomize name if both exist (the controller reads it).
	@SAT_CM=$$(kubectl get configmap wva-saturation-scaling-config \
		-n $(BENCHMARK_NAMESPACE) -o name 2>/dev/null | sed 's|configmap/||'); \
	if [ -z "$$SAT_CM" ]; then \
		SAT_CM=$$(kubectl get configmap -n $(BENCHMARK_NAMESPACE) \
			-o name 2>/dev/null | grep "saturation-scaling-config" | head -1 | sed 's|configmap/||'); \
	fi; \
	if [ -z "$$SAT_CM" ]; then \
		echo "ERROR: saturation-scaling-config ConfigMap not found in namespace $(BENCHMARK_NAMESPACE)"; \
		exit 1; \
	fi; \
	echo "Patching ConfigMap $$SAT_CM to enable V2 saturation analyzer..."; \
	kubectl patch configmap "$$SAT_CM" -n $(BENCHMARK_NAMESPACE) --type=merge \
		-p '{"data":{"default":"analyzers:\n  - name: saturation\nkvCacheThreshold: 0.80\nqueueLengthThreshold: 5\nkvSpareTrigger: 0.1\nqueueSpareTrigger: 3\nenableLimiter: false\n"}}'
	$(MAKE) benchmark-restart-controller BENCHMARK_NAMESPACE=$(BENCHMARK_NAMESPACE)

WVA_ANALYZERS ?= saturation,throughput

.PHONY: benchmark-show-analyzers
benchmark-show-analyzers: ## Print the live WVA analyzer config (set BENCHMARK_NAMESPACE=<namespace>)
	@if [ -z "$(BENCHMARK_NAMESPACE)" ]; then \
		echo "ERROR: BENCHMARK_NAMESPACE is required. Usage: make benchmark-show-analyzers BENCHMARK_NAMESPACE=<namespace>"; \
		exit 1; \
	fi
	@python3 $(CURDIR)/hack/benchmark/set_analyzers.py -n $(BENCHMARK_NAMESPACE) --show

.PHONY: benchmark-set-analyzers
benchmark-set-analyzers: ## Set the WVA analyzer list, leaving all other config keys untouched, then restart the controller (set BENCHMARK_NAMESPACE=<namespace>, WVA_ANALYZERS=saturation[,throughput])
	@if [ -z "$(BENCHMARK_NAMESPACE)" ]; then \
		echo "ERROR: BENCHMARK_NAMESPACE is required. Usage: make benchmark-set-analyzers BENCHMARK_NAMESPACE=<namespace> WVA_ANALYZERS=saturation"; \
		exit 1; \
	fi
	@# Unlike benchmark-enable-v2-saturation (which rewrites the whole payload,
	@# thresholds included), this edits only the analyzers: block -- so an A/B
	@# arm switch changes exactly the analyzer set and nothing else.
	python3 $(CURDIR)/hack/benchmark/set_analyzers.py \
		-n $(BENCHMARK_NAMESPACE) --analyzers $(WVA_ANALYZERS)
	$(MAKE) benchmark-restart-controller BENCHMARK_NAMESPACE=$(BENCHMARK_NAMESPACE)

.PHONY: benchmark-restart-controller
benchmark-restart-controller: ## Restart WVA controller to flush in-memory state (e.g., k2 history between runs)
	@if [ -z "$(BENCHMARK_NAMESPACE)" ]; then \
		echo "ERROR: BENCHMARK_NAMESPACE is required. Usage: make benchmark-restart-controller BENCHMARK_NAMESPACE=<namespace>"; \
		exit 1; \
	fi
	@# Detect the controller deployment name: Kustomize installs use wva-controller-manager,
	@# Helm-based installs use workload-variant-autoscaler-controller-manager.
	@DEPLOY=$$(kubectl get deploy -n $(BENCHMARK_NAMESPACE) \
		-l app.kubernetes.io/name=workload-variant-autoscaler \
		-o name 2>/dev/null | head -1); \
	DEPLOY=$${DEPLOY:-$(WVA_CONTROLLER_DEPLOY)}; \
	echo "Restarting $$DEPLOY..."; \
	kubectl rollout restart -n $(BENCHMARK_NAMESPACE) $$DEPLOY; \
	kubectl rollout status -n $(BENCHMARK_NAMESPACE) $$DEPLOY --timeout=$(WVA_ROLLOUT_TIMEOUT)

BURSTY_WORKLOAD    ?= bursty.yaml
BENCHMARK_WAIT_TIMEOUT ?= 7200
BENCHMARK_HARNESS_MEMORY ?= 40Gi

.PHONY: benchmark-run-bursty
benchmark-run-bursty: ## Run bursty traffic benchmark using inference-perf multi-stage rates (set BENCHMARK_NAMESPACE=<namespace>, MODEL_ID=<model>)
	@if [ -z "$(BENCHMARK_NAMESPACE)" ]; then \
		echo "ERROR: BENCHMARK_NAMESPACE is required. Usage: make benchmark-run-bursty BENCHMARK_NAMESPACE=<namespace>"; \
		exit 1; \
	fi
	@if [ -f "$(BENCHMARK_SCENARIOS_DIR)/$(BURSTY_WORKLOAD).in" ]; then \
		cp "$(BENCHMARK_SCENARIOS_DIR)/$(BURSTY_WORKLOAD).in" \
		   "$(BENCHMARK_REPO_DIR)/workload/profiles/inference-perf/$(BURSTY_WORKLOAD).in"; \
	fi
	@echo "Patching harness memory to $(BENCHMARK_HARNESS_MEMORY)..."
	@sed -i.bak 's/memory: 32Gi/memory: $(BENCHMARK_HARNESS_MEMORY)/' \
		$(BENCHMARK_REPO_DIR)/config/templates/values/defaults.yaml
	$(LLMDBENCHMARK) $(BENCHMARK_CLI_FLAGS) run \
		-p $(BENCHMARK_NAMESPACE) \
		-l inference-perf \
		-w $(BURSTY_WORKLOAD) \
		-U $(BENCHMARK_GATEWAY_URL) \
		$(if $(BENCHMARK_MODEL_ID),-m $(BENCHMARK_MODEL_ID),) \
		$(if $(filter true,$(BENCHMARK_MONITORING)),--monitoring,); \
	rc=$$?; \
	mv $(BENCHMARK_REPO_DIR)/config/templates/values/defaults.yaml.bak \
	   $(BENCHMARK_REPO_DIR)/config/templates/values/defaults.yaml; \
	exit $$rc

.PHONY: benchmark-run-all
benchmark-run-all: ## Run all scenarios: teardown → standup → run per scenario (set BENCHMARK_NAMESPACE=<namespace>, MODEL_ID=<model>)
	@if [ -z "$(BENCHMARK_NAMESPACE)" ]; then \
		echo "ERROR: BENCHMARK_NAMESPACE is required. Usage: make benchmark-run-all BENCHMARK_NAMESPACE=<namespace>"; \
		exit 1; \
	fi
	@for scenario in $(BENCHMARK_SCENARIOS_DIR)/*.yaml.in; do \
		scenario_name=$$(basename "$$scenario" .in); \
		echo ""; \
		echo "=========================================="; \
		echo "[1/3] Tearing down before: $$scenario_name"; \
		echo "=========================================="; \
		$(LLMDBENCHMARK) $(BENCHMARK_CLI_FLAGS) teardown \
			-p $(BENCHMARK_NAMESPACE) || true; \
		echo ""; \
		echo "=========================================="; \
		echo "[2/3] Standing up for: $$scenario_name"; \
		echo "=========================================="; \
		$(LLMDBENCHMARK) $(BENCHMARK_CLI_FLAGS) standup \
			-p $(BENCHMARK_NAMESPACE) \
			$(if $(BENCHMARK_MODEL_ID),-m $(BENCHMARK_MODEL_ID),) \
			$(if $(filter true,$(BENCHMARK_MONITORING)),--monitoring,) || { \
			echo "ERROR: Standup failed for $$scenario_name"; \
			exit 1; \
		}; \
		echo ""; \
		echo "=========================================="; \
		echo "[3/3] Running scenario: $$scenario_name"; \
		echo "=========================================="; \
		$(LLMDBENCHMARK) $(BENCHMARK_CLI_FLAGS) run \
			-p $(BENCHMARK_NAMESPACE) \
			-l $(BENCHMARK_HARNESS) \
			-w "$$scenario_name" \
			$(if $(BENCHMARK_MODEL_ID),-m $(BENCHMARK_MODEL_ID),) || { \
			echo "ERROR: Scenario $$scenario_name failed"; \
			exit 1; \
		}; \
	done
	@echo ""
	@echo "=========================================="
	@echo "All scenarios completed successfully"
	@echo "=========================================="

.PHONY: benchmark-teardown
benchmark-teardown: ## Tear down the benchmark environment (set BENCHMARK_NAMESPACE=<namespace>)
	@if [ -z "$(BENCHMARK_NAMESPACE)" ]; then \
		echo "ERROR: BENCHMARK_NAMESPACE is required. Usage: make benchmark-teardown BENCHMARK_NAMESPACE=<namespace>"; \
		exit 1; \
	fi
	$(LLMDBENCHMARK) $(BENCHMARK_CLI_FLAGS) teardown \
		-p $(BENCHMARK_NAMESPACE)

.PHONY: benchmark-full
benchmark-full: benchmark-standup benchmark-run-all benchmark-teardown ## Full lifecycle: standup -> run all scenarios -> teardown

# Stub for llm-d nightly reusable workflows (test_target=nightly-test-llm-d)
# No-op; temporarily satisfies nightly CI make invocation
# TODO: add nightly guide tests here
.PHONY: nightly-test-llm-d
nightly-test-llm-d: ## Nightly CI: noop; use as test_target instead of empty string
	@:

# Canonical target for llm-d-infra nightly reusables: ENVIRONMENT=openshift|kubernetes
# Deploys WVA + monitoring + scaler backend only. llm-d model serving is deployed separately
# by the nightly workflow's custom_deploy_script (kustomize + GAIE helm from llm-d/llm-d guide).
.PHONY: nightly-deploy-wva-guide
nightly-deploy-wva-guide: ## Nightly: WVA controller + monitoring stack from job env (WVA_NS <- WVA_NAMESPACE or CONTROLLER_NAMESPACE)
	# Note: CKS callers with resource constraints should disable nodeExporter by patching kube-prometheus-stack post-install.
	@WVA_NS="$${WVA_NS:-$${WVA_NAMESPACE:-$${CONTROLLER_NAMESPACE:-}}}" \
	ENVIRONMENT="$${ENVIRONMENT:-openshift}" \
	./deploy/install.sh

.PHONY: lint
lint: golangci-lint ## Run golangci-lint linter
	$(GOLANGCI_LINT) run

.PHONY: lint-deploy-scripts
lint-deploy-scripts: ## Run bash -n for deploy/install.sh, deploy/lib/*.sh, and deploy plugins
	@echo "Syntax-checking deploy shell scripts..."
	@bash -n deploy/install.sh
	@bash -n deploy/install-epp.sh
	@for script in deploy/lib/*.sh; do bash -n "$$script"; done
	@for script in deploy/*/install.sh; do if [ -f "$$script" ]; then bash -n "$$script"; fi; done
	@for script in deploy/kind-emulator/*.sh; do if [ -f "$$script" ]; then bash -n "$$script"; fi; done
	@echo "deploy script syntax OK"

.PHONY: smoke-deploy-scripts
smoke-deploy-scripts: lint-deploy-scripts ## Non-interactive deploy script smoke check (source order + arg parsing)
	@echo "Running deploy script smoke check..."
	@SKIP_CHECKS=true ENVIRONMENT=kubernetes ./deploy/install.sh --help >/dev/null
	@echo "deploy script smoke OK"

.PHONY: lint-fix
lint-fix: golangci-lint ## Run golangci-lint linter and perform fixes
	$(GOLANGCI_LINT) run --fix

.PHONY: lint-config
lint-config: golangci-lint ## Verify golangci-lint linter configuration
	$(GOLANGCI_LINT) config verify

##@ Build

.PHONY: build
build: manifests generate fmt vet ## Build manager binary.
	go build -o bin/manager cmd/main.go

.PHONY: run
run: manifests generate fmt vet ## Run a controller from your host.
	go run ./cmd/main.go

# If you wish to build the manager image targeting other platforms you can use the --platform flag.
# (i.e. docker build --platform linux/arm64). However, you must enable docker buildKit for it.
# More info: https://docs.docker.com/develop/develop-images/build_enhancements/
.PHONY: docker-build
docker-build: ## Build docker image with the manager.
	$(CONTAINER_TOOL) build -t ${IMG} .

.PHONY: docker-push
docker-push: ## Push docker image with the manager.
	$(CONTAINER_TOOL) push ${IMG}

# PLATFORMS defines the target platforms for the manager image be built to provide support to multiple
# architectures. (i.e. make docker-buildx IMG=myregistry/mypoperator:0.0.1). To use this option you need to:
# - be able to use docker buildx. More info: https://docs.docker.com/build/buildx/
# - have enabled BuildKit. More info: https://docs.docker.com/develop/develop-images/build_enhancements/
# - be able to push the image to your registry (i.e. if you do not set a valid value via IMG=<myregistry/image:<tag>> then the export will fail)
# To adequately provide solutions that are compatible with multiple platforms, you should consider using this option.
PLATFORMS ?= linux/arm64,linux/amd64
BUILDER_NAME ?= workload-variant-autoscaler-builder

.PHONY: docker-buildx
docker-buildx: ## Build and push docker image for the manager for cross-platform support
	# copy existing Dockerfile and insert --platform=${BUILDPLATFORM} into Dockerfile.cross, and preserve the original Dockerfile
	sed -e '1 s/\(^FROM\)/FROM --platform=\$$\{BUILDPLATFORM\}/; t' -e ' 1,// s//FROM --platform=\$$\{BUILDPLATFORM\}/' Dockerfile > Dockerfile.cross
	- $(CONTAINER_TOOL) buildx create --name workload-variant-autoscaler-builder
	$(CONTAINER_TOOL) buildx use workload-variant-autoscaler-builder
	- $(CONTAINER_TOOL) buildx build --push --platform=$(PLATFORMS) --tag ${IMG} -f Dockerfile.cross .
	- $(CONTAINER_TOOL) buildx rm workload-variant-autoscaler-builder
	rm Dockerfile.cross

##@ Deployment

ifndef ignore-not-found
  ignore-not-found = false
endif


##@ Dependencies

## Location to install dependencies to
LOCALBIN ?= $(shell pwd)/bin
$(LOCALBIN):
	mkdir -p $(LOCALBIN)

## Tool Binaries
KUBECTL ?= kubectl
KIND ?= kind
KUSTOMIZE ?= $(LOCALBIN)/kustomize
CONTROLLER_GEN ?= $(LOCALBIN)/controller-gen
ENVTEST ?= $(LOCALBIN)/setup-envtest
GOLANGCI_LINT = $(LOCALBIN)/golangci-lint
HELM ?= $(LOCALBIN)/helm

## Tool Versions
KUSTOMIZE_VERSION ?= v5.6.0
CONTROLLER_TOOLS_VERSION ?= v0.17.2
#ENVTEST_VERSION is the version of controller-runtime release branch to fetch the envtest setup script (i.e. release-0.20)
ENVTEST_VERSION ?= $(shell go list -m -f "{{ .Version }}" sigs.k8s.io/controller-runtime | awk -F'[v.]' '{printf "release-%d.%d", $$2, $$3}')
#ENVTEST_K8S_VERSION is the version of Kubernetes to use for setting up ENVTEST binaries (i.e. 1.31)
ENVTEST_K8S_VERSION ?= $(shell go list -m -f "{{ .Version }}" k8s.io/api | awk -F'[v.]' '{printf "1.%d", $$3}')
GOLANGCI_LINT_VERSION ?= v2.8.0
HELM_VERSION ?= v3.17.1

.PHONY: kustomize
kustomize: $(KUSTOMIZE) ## Download kustomize locally if necessary.
$(KUSTOMIZE): $(LOCALBIN)
	$(call go-install-tool,$(KUSTOMIZE),sigs.k8s.io/kustomize/kustomize/v5,$(KUSTOMIZE_VERSION))

.PHONY: controller-gen
controller-gen: $(CONTROLLER_GEN) ## Download controller-gen locally if necessary.
$(CONTROLLER_GEN): $(LOCALBIN)
	$(call go-install-tool,$(CONTROLLER_GEN),sigs.k8s.io/controller-tools/cmd/controller-gen,$(CONTROLLER_TOOLS_VERSION))


.PHONY: setup-envtest
setup-envtest: envtest ## Download the binaries required for ENVTEST in the local bin directory.
	@echo "Setting up envtest binaries for Kubernetes version $(ENVTEST_K8S_VERSION)..."
	@$(ENVTEST) use $(ENVTEST_K8S_VERSION) --bin-dir $(LOCALBIN) -p path || { \
		echo "Error: Failed to set up envtest binaries for version $(ENVTEST_K8S_VERSION)."; \
		exit 1; \
	}

.PHONY: envtest
envtest: $(ENVTEST) ## Download setup-envtest locally if necessary.
$(ENVTEST): $(LOCALBIN)
	$(call go-install-tool,$(ENVTEST),sigs.k8s.io/controller-runtime/tools/setup-envtest,$(ENVTEST_VERSION))

.PHONY: golangci-lint
golangci-lint: $(GOLANGCI_LINT) ## Download golangci-lint locally if necessary.
$(GOLANGCI_LINT): $(LOCALBIN)
	@[ -f "$(LOCALBIN)/golangci-lint-$(GOLANGCI_LINT_VERSION)" ] || { \
	set -e; \
	echo "Downloading golangci-lint $(GOLANGCI_LINT_VERSION)"; \
	curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $(LOCALBIN) $(GOLANGCI_LINT_VERSION); \
	if [ -f "$(LOCALBIN)/golangci-lint" ]; then \
		mv $(LOCALBIN)/golangci-lint $(LOCALBIN)/golangci-lint-$(GOLANGCI_LINT_VERSION); \
	fi; \
	} ;\
	ln -sf golangci-lint-$(GOLANGCI_LINT_VERSION) $(GOLANGCI_LINT)

.PHONY: helm
helm: $(HELM) ## Download helm locally if necessary.
$(HELM): $(LOCALBIN)
	@[ -f "$(LOCALBIN)/helm-$(HELM_VERSION)" ] || { \
	set -e; \
	echo "Downloading helm $(HELM_VERSION)"; \
	curl -sSfL https://get.helm.sh/helm-$(HELM_VERSION)-$(shell go env GOOS)-$(shell go env GOARCH).tar.gz | tar xz --no-same-owner -C $(LOCALBIN) --strip-components=1 $(shell go env GOOS)-$(shell go env GOARCH)/helm; \
	mv $(LOCALBIN)/helm $(LOCALBIN)/helm-$(HELM_VERSION); \
	} ;\
	ln -sf helm-$(HELM_VERSION) $(HELM)

# go-install-tool will 'go install' any package with custom target and name of binary, if it doesn't exist
# $1 - target path with name of binary
# $2 - package url which can be installed
# $3 - specific version of package
define go-install-tool
@[ -f "$(1)-$(3)" ] || { \
set -e; \
package=$(2)@$(3) ;\
echo "Downloading $${package}" ;\
rm -f $(1) || true ;\
GOBIN=$(LOCALBIN) go install $${package} ;\
mv $(1) $(1)-$(3) ;\
} ;\
ln -sf $(1)-$(3) $(1)
endef


include config/samples/hpa/co-ordinator/poc.mk
