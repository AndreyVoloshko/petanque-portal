$(function() {
    //Toggle Auth forms
    $('#login-form-link').click(function(e) {
		$("#login-form").delay(100).fadeIn(100);
 		$("#register-form").fadeOut(100);
		$('#register-form-link').removeClass('active');
		$(this).addClass('active');
		e.preventDefault();
	});
	$('#register-form-link').click(function(e) {
		$("#register-form").delay(100).fadeIn(100);
 		$("#login-form").fadeOut(100);
		$('#login-form-link').removeClass('active');
		$(this).addClass('active');
		e.preventDefault();
	});

    //init tooltips
    $('[data-toggle="tooltip"]').tooltip();

    //init tabs
    $('.nav-tabs a').click(function (e) {
      e.preventDefault();
      $(this).tab('show');
    });
    $('.nav-tabs a.active').click();

    // Javascript to enable link to tab
    var url = document.location.toString();
    if (url.match('#')) {
        $('a[href="#' + url.split('#')[1] + '"]').tab('show');
    }
});