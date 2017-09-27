docs:
	$(MAKE) -C docs html

watch-docs:
	watchmedo shell-command \
	--patterns="*.css;*.js;*.html;*.rst;*.css_t" \
	--ignore-pattern='*build*' --recursive \
	--command='make docs' docs

.PHONY: docs, watch-docs

.NOTPARALLEL:

