.PHONY: help install dev build test bench lint syntax forge-build forge-test \
        compose-up compose-down compose-config db-init mantle-probe deploy-athean \
        deploy-restraint clean

PYTHON ?= python
PYTHONPATH_ALL = packages/athean-core/src:services/areopagus/src:services/apollo/src:services/boule/src:services/argos/src:services/strategos/src:services/parthenon/src:services/ostrakon/src:services/moirai/src:services/underworld/src:apps/api/src

help:
	@echo "Athean Trades — common tasks"
	@echo ""
	@echo "  install         pnpm install + uv sync per service"
	@echo "  dev             turbo run dev --parallel"
	@echo "  build           turbo run build"
	@echo "  test            full python + foundry + integration sweep"
	@echo "  bench           tests/bench.py — correctness + microbench"
	@echo "  lint            turbo lint"
	@echo "  syntax          py_compile every python source"
	@echo ""
	@echo "  compose-up      docker compose up -d"
	@echo "  compose-down    docker compose down"
	@echo "  compose-config  docker compose config (validates yaml)"
	@echo ""
	@echo "  db-init         psql -f db/schema.sql"
	@echo "  mantle-probe    hit Mantle Sepolia RPC via the project's wiring"
	@echo ""
	@echo "  forge-build     forge build --root contracts"
	@echo "  forge-test      forge test --root contracts"
	@echo "  deploy-athean broadcast DeployPantheon to Mantle Sepolia"
	@echo "  deploy-restraint broadcast DeployRestraint to Mantle Sepolia"
	@echo ""
	@echo "  clean           remove pycache + node_modules build artifacts"

install:
	pnpm install
	@for svc in packages/athean-core services/* apps/api; do \
		if [ -f $$svc/pyproject.toml ]; then \
			echo "uv sync $$svc"; \
			(cd $$svc && uv sync); \
		fi; \
	done

dev:
	turbo run dev --parallel

build:
	turbo run build

syntax:
	$(PYTHON) tests/_syntax_check.py

bench:
	$(PYTHON) tests/bench.py

test: syntax forge-test
	PYTHONPATH=$(PYTHONPATH_ALL) $(PYTHON) -m pytest tests/test_pipeline_integration.py -q

lint:
	turbo run lint

forge-build:
	forge build --root contracts

forge-test:
	forge test --root contracts

compose-up:
	docker compose up -d

compose-down:
	docker compose down

compose-config:
	docker compose config > /dev/null && echo "docker-compose.yml OK"

db-init:
	psql $${DATABASE_URL:-postgresql://athean:athean@localhost:5432/athean} -f db/schema.sql

mantle-probe:
	$(PYTHON) tests/mantle_probe.py

deploy-athean:
	@test -n "$$PRIVATE_KEY" || (echo "PRIVATE_KEY env required" && exit 1)
	forge script --root contracts script/DeployPantheon.s.sol:DeployPantheon \
		--rpc-url mantle_sepolia --broadcast -vvv

deploy-restraint:
	@test -n "$$PRIVATE_KEY" || (echo "PRIVATE_KEY env required" && exit 1)
	forge script --root contracts script/DeployRestraint.s.sol:DeployRestraint \
		--rpc-url mantle_sepolia --broadcast -vvv

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	find . -type d -name node_modules -prune -exec rm -rf {} +
	find . -type d -name .next -prune -exec rm -rf {} +
	rm -rf contracts/out contracts/cache
