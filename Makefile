.PHONY: test evals demo

test:
	python -m pytest -q

evals:
	python -m core.evals.runner --dataset evals/datasets/demo.jsonl --docs evals/documentos \
		--min-exactitud 90 --min-fidelidad 100 --min-rechazo 100

demo:
	python -m apps.api.demo
