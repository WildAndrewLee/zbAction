(function(){
	$('.select').focus(function(){
		$(this).select();
	});

	hljs.initHighlightingOnLoad();

	$('pre').has('code').highlight();
})();