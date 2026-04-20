.PHONY: metar taf

metar:
	PYTHONPATH=src python -m weather_decoder metar $(ARGS)

taf:
	PYTHONPATH=src python -m weather_decoder taf $(ARGS)
