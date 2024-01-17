$(document).ready(function(){

    // Adjust the width of class boxes based on the width of table cells
    function adjustClassBoxWidth() {
        var tdWidth = $('.table td').width();
        var classBoxWidth = tdWidth - 10;
        $('.class-box').width(classBoxWidth);
    }

    adjustClassBoxWidth();


    // Adjust the width of class boxes when resizing window
    $(window).resize(function () {
        adjustClassBoxWidth();
    });

    // Toggle the sidebar visibility and adjust widths accordingly
    $("#toggle-sidebar").click(function(){
        if ($(".sidebar").is(":visible")) {
            $(".sidebar").hide();
            $(".main-panel").css("width", "100%");
            adjustClassBoxWidth();
        } else {
            $(".sidebar").show();
            $(".main-panel").css("width", "calc(100% - 260px)");
            adjustClassBoxWidth();
        }
    });

    // Initialize perfectScrollbar for various elements
    $('.sidebar .sidebar-wrapper, .main-panel, .scroll-table, .scroll-timetable, .dropdown-menu').perfectScrollbar();
    $('.scroll-table-body').perfectScrollbar({
        suppressScrollX: true
    });

    // Switch between sections
    $('.switch-button').on('click', function() {
        $('.switch-button').removeClass('btn-success');
        $(this).addClass('btn-success');
        $('.target-table').hide();
        var targetTable = $(this).data('target');
        $('#' + targetTable).show();
    });

    // Switch between sections and forms
    function toggleSectionAndForm() {
        $(document).on('click', '.section-form-btn', function() {
            var parent = $(this).closest('.section, .form');
            var target = parent.data('target');
            $('.section-' + target + ', .form-' + target).toggle();
        });
    }

    toggleSectionAndForm();


    // Open comment cell
    $(document).on("click", ".comment-cell", function () {
        var commentFormContainer = $(this).find(".comment-form-container");
        var commentContainer = $(this).find(".comment-container");
        commentFormContainer.show();
        commentContainer.hide();
        if (!commentFormContainer.data("filled")) {
            var commentText = commentContainer.text();
            commentFormContainer.find("textarea[name='comment']").val(commentText.trim());
            commentFormContainer.data("filled", true);
        }
    });

    // Close comment cell by clicking anywhere
    $(document).mouseup(function (e) {
        var container = $(".comment-form-container");

        if (!container.is(e.target) && container.has(e.target).length === 0) {
            container.hide();
            container.closest(".comment-cell").find(".comment-container").show();
            container.data("filled", false);
        }
    });

    // Comment submission to the database
    $(document).on("submit", ".comment-form", function (e) {
        e.preventDefault();

        var personId = $(this).data("person-id");
        var commentText = $(this).find("textarea[name='comment']").val();
        var commentContainer = $(this).closest(".comment-cell").find(".comment-container");
        var commentFormContainer = $(this).closest(".comment-cell").find(".comment-form-container");

        $.ajax({
            type: "POST",
            url: "/add-comment",
            data: {
                person_id: personId,
                comment: commentText
            },
            success: function (response) {
                commentContainer.text(response);
            },
            error: function (error) {
                alert('Ошибка при добавлении комментария');
                console.error(error);
            }
        });

        commentContainer.show();
        commentFormContainer.hide();
    });

    // Date and time pickers settings
    $.datepicker.setDefaults( $.datepicker.regional[ "ru" ] );

    $(".datepicker").datepicker({
        dateFormat: "dd.mm.yy",
        changeYear: true,
    });

    $('.timepicker').wickedpicker();


    // Hide date and time pickers when scrolling
    $(".main-panel").on("scroll", function() {
        if ($(".datepicker").datepicker("widget").is(":visible")) {
            $(".datepicker").datepicker("hide");
        }
        if ($(".timepicker").wickedpicker("widget").is(":visible")) {
            $(".timepicker").wickedpicker("hide");
        }
    });

    // function to handle the change event for the status select dropdown
    function handleStatusChange(statusSelect, pauseDateId, leavingReasonId) {
        const selectedStatus = statusSelect.val();
        const pauseDate = $(pauseDateId);
        const leavingReason = $(leavingReasonId);

        if (selectedStatus === "Пауза") {
            pauseDate.show();
            leavingReason.hide();
        } else if (selectedStatus === "Закрыт") {
            pauseDate.hide();
            leavingReason.show();
        } else {
            pauseDate.hide();
            leavingReason.hide();
        }
    }

    // Handle status select changing for children
    $("#status-select").on("change", function () {
        handleStatusChange($(this), "#pause-date", "#leaving-reason");
    });

    $("#status-select").trigger("change");


    // Handle status select changing for adults
    $("#status-select-adult").on("change", function () {
        handleStatusChange($(this), "#pause-date-adult", "#leaving-reason-adult");
    });

    // Handle the change event for the relation select dropdown when adding or editing a new client
    $("#contact-sections, #show-contacts").on("change", ".contact-relation", function () {
        var relationSelector = $(this);
        var contactSection = relationSelector.closest(".contact-section");
        var otherRelationRow = contactSection.find(".relation-other-row");
        var contactInfo = contactSection.find(".contact-info");
        var contactSelection = contactSection.find(".contact_selection");

        if (relationSelector.val() === "Другое") {
            otherRelationRow.show();
            contactInfo.show();
            contactSelection.show();
        } else if (relationSelector.val() === "Сам ребенок") {
            otherRelationRow.hide();
            contactInfo.hide();
            contactSelection.hide();
        } else {
            otherRelationRow.hide();
            contactInfo.show();
            contactSelection.show();
        }
    });

    // Search in table
    $('#search').keyup(function() {
        var val = $.trim($(this).val()).replace(/ +/g, ' ').toLowerCase();
        var table = $('.scroll-table-body');

        table.find('tbody tr').show().filter(function() {
            var text = $(this).text().replace(/\s+/g, ' ').toLowerCase();
            return !~text.indexOf(val);
        }).hide();

        table.perfectScrollbar('update');

        var visibleRow = table.find('tbody tr:visible:first');
        if (visibleRow.length > 0) {
            table.scrollTop(table.scrollTop() + visibleRow.position().top);
        }
    });

    // Function to update client information when adding or editing a new client
    function updatePersonInformation(selector, section) {
        var personId = Number(selector.val());
        var selectedPerson = clientsData.filter(function(person) {
            return person.id === personId;
        });
        var selectedSection = selector.closest(section);
        var personInfoBasic = selectedSection.find(".person-info-basic")
        var personInfoContacts = selectedSection.find(".person-info-contacts")

        if (selectedPerson.length > 0) {
            personInfoBasic.html(`
                <div class="row">
                    <label class="control-label col-md-3">Фамилия:</label>
                    <div class="col-md-5">
                        <p class="form-control">${selectedPerson[0].last_name}</p>
                    </div>
                </div>
                <div class="row">
                    <label class="control-label col-md-3">Имя:</label>
                    <div class="col-md-5">
                        <p class="form-control">${selectedPerson[0].first_name}</p>
                    </div>
                </div>
                <div class="row">
                    <label class="control-label col-md-3">Отчество:</label>
                    <div class="col-md-5">
                        <p class="form-control">${selectedPerson[0].patronym}</p>
                    </div>
                </div>
            `);

            personInfoContacts.html(`
                <div class="row">
                    <label class="control-label col-md-3">Телеграм:</label>
                    <div class="col-md-3">
                        <p class="form-control">${selectedPerson[0].telegram}</p>
                    </div>
                </div>
                <div class="row">
                    <label class="control-label col-md-3">Телефон:</label>
                    <div class="col-md-3">
                        <p class="form-control">${selectedPerson[0].phone}</p>
                    </div>
                </div>
                <div class="row">
                    <label class="control-label col-md-3">Другое:</label>
                    <div class="col-md-3">
                        <p class="form-control">${selectedPerson[0].other_contact}</p>
                    </div>
                </div>
            `);
        } else {
            personInfoBasic.html("");
            personInfoContacts.html("");
        }
    }

    // Function to handle the change event for selection between adding a new person and choosing existing
    function personSelectChange(selector, personSection) {
        var selectorVal = selector.val();
        var prefix = personSection.replace("-section", "-");
        var parentSection = selector.closest(personSection);
        var personOptionsRow = parentSection.find(prefix + "options-row");
        var personInput = parentSection.find(prefix + "input");
        var personInformation = parentSection.find(prefix + "information");
        var personSelector = parentSection.find(prefix + "options");

        if (selectorVal === "Добавить") {
            personInput.show();
            personOptionsRow.hide();
            personInformation.hide();
        } else {
            personInput.hide();
            personOptionsRow.show();
            personInformation.show();
            personSelector[0].selectize.trigger( "change" );
        }
    }

    // Handle the change event for contact selection
    $("#contact-sections, #new-contact-form").on("change", ".contact-select", function () {
        personSelectChange($(this), ".contact-section");
    });

    $(".contact-select").trigger("change");


    // Update contact information based on selected person
    $("#contact-sections, #new-contact-form").on("change", ".contact-options", function() {
        updatePersonInformation($(this), ".contact-section");
    });

    // Handle the change event for client selection
    $(".client-section").on("change", ".client-select", function () {
         personSelectChange($(this), ".client-section");
    });

    $(".client-select").trigger("change");


    // Update client information based on selected person
    $(".client-section").on("change", ".client-options", function() {
        updatePersonInformation($(this), ".client-section");
    });

    var contactCount = 1
    // Function to add a new contact section dynamically
    function addContactSection() {
        contactCount++;

        var firstContactSection = $(".contact-section").first()
        firstContactSection.find('select').each(function() {
            if ($(this)[0].selectize) {
                inputValue = $(this)[0].selectize.getValue()
                $(this)[0].selectize.destroy();
            }
        });

        var contactSection = firstContactSection.clone();

        var firstSelectizeElement = firstContactSection.find(".contact-options.select-search");
        initializeSelectize(firstSelectizeElement);
        firstSelectizeElement[0].selectize.setValue(inputValue);

        contactSection.find(".contact-radio").prop("checked", false);
        contactSection.attr("id", "contact-section-" + contactCount);
        contactSection.find(".contact-relation").val("Мама");
        contactSection.find(".relation-other-row").hide();
        contactSection.find(".contact-select").val("Добавить");
        contactSection.find(".contact-options-row").hide();
        contactSection.find(".contact-input").show();
        contactSection.find(".contact-information").hide();

        contactSection.find("select, input[type='text']").each(function() {
            var originalName = $(this).attr("name");
            if (originalName) {
                var newName = originalName.replace("_1", "_" + contactCount);
                $(this).attr("name", newName);
                if ($(this).is("input[type='text']")) {
                    $(this).val("");
                }
            }
        });
        contactSection.find("input[type='radio']").each(function() {
            var originalValue = $(this).val();
            var newValue = originalValue.replace("_1", "_" + contactCount);
            $(this).val(newValue);
        });

        return contactSection;
    }

    // Add a new contact form when adding a new client
    $("#add-contact-btn").click(function() {
        var newContactSection = addContactSection();
        newContactSection.appendTo("#contact-sections");

        var newSelectizeElement = newContactSection.find(".contact-options.select-search");
        initializeSelectize(newSelectizeElement);

        if (contactCount >= 2) {
            $("#remove-contact").show();
        }
    });

    // Remove a contact form when adding a new client
    $("#remove-contact").click(function() {
        $("#contact-sections .contact-section:last").remove();
        contactCount--;
        if (contactCount === 1) {
            $("#remove-contact").hide();
        }
    });

    // Pass contact count information when submitting a new client
    $("#submit-btn").click(function() {
        $('#contact-count').val(contactCount);
    });

    // Function to switch between different sections based on button clicks
    function handleTabButtonClick(buttonId) {
        var targetId = '#' + buttonId.replace('-btn', '');
        $('#show-subjects, #show-contacts, #show-subscriptions').hide();
        $(targetId).show();
    }

    // Show different sections based on button clicks
    $('#show-contacts-btn, #show-subjects-btn, #show-subscriptions-btn').click(function () {
        handleTabButtonClick(this.id);
    });

    // Toggle new contact form when editing a client
    $('#show-new-contact-btn, #hide-new-contact-btn').click(function () {
        $('#show-new-contact, #new-contact-form').toggle();
    });

    // Toggle client selector based on button clicks
    $("#add-client-btn, #cancel-add-client-btn").click(function() {
        $("#clientSelector, #add-client-btn").toggle();
    });

    // Show dropdown by clicking on a specific object
    window.showDropdown = function(objectId, event) {
        $('.dropdown-content').hide();
        $(`#dropdown-${objectId}`).toggle().css({
            top: event.offsetY,
            left: event.offsetX
        });
        event.stopPropagation();
    }

    // Hide dropdown when clicking anywhere
    $(document).on('click', function () {
        $('.dropdown-content').hide();
    });

    // Handle the change event for lesson subject selector
    $('.lesson-subject-select').change(function () {
        var subjectId = Number($(this).val());
        var selectedSubject = lessonSubjectsData.filter(function(subject) {
            return subject.id === subjectId;
        });

        const lessonSelector = $('.lesson-select');
        lessonSelector.empty();

        $.each(selectedSubject[0].lessons, function (index, lesson) {
            lessonSelector.append(`<option value="${index}">${lesson}</option>`);
        });

    });

    // Trigger selector change when lesson modal is shown
    $('.lesson-modal-trigger').on('click', function () {
        var lessonModalId = $(this).data('target');
        var lessonModal = $(lessonModalId);
        lessonModal.on('shown.bs.modal', function () {
            var lessonSubjectSelector = $(this).find('.lesson-subject-select');
            lessonSubjectSelector.trigger("change");
        });

    });

    // Handle the change event for subscription subject selector
    $('.subscription-subject-select').change(function () {
        var subjectId = Number($(this).val());
        var selectedSubject = subscriptionSubjectsData.filter(function(subject) {
            return subject.id === subjectId;
        });

        const subscriptionTypeSelector = $('.subscription-type-select');
        subscriptionTypeSelector.empty();

        $.each(selectedSubject[0].subscription_types_info, function (index, subscriptionType) {
            subscriptionTypeSelector.append(`<option value="${index}">${subscriptionType}</option>`);
        });

        subscriptionTypeSelector.change(function () {
            var subscriptionType = $(this).val();
            const priceDisplay = $('.price-display');
            priceDisplay.html(`<b>${selectedSubject[0].price_info[subscriptionType]}</b>`);
        });

        subscriptionTypeSelector.trigger("change");
    });

    // Trigger selectors change when subscription modal is shown
    $('.subscription-modal-trigger').on('click', function () {
        var subscriptionModalId = $(this).data('target');
        var subscriptionModal = $(subscriptionModalId);
        var subscriptionSubjectSelector = subscriptionModal.find('.subscription-subject-select');
        subscriptionSubjectSelector.trigger("change");
    });

    // Handle the change event for employee selection
    $(".employee-section").on("change", ".employee-select", function () {
         personSelectChange($(this), ".employee-section");
    });

    $(".employee-select").trigger("change");


    // Update employee information based on selected person
    $(".employee-section").on("change", ".employee-options", function() {
        updatePersonInformation($(this), ".employee-section");
    });

    // Show subjects selector when checking teacher option
    $(".employee-section").on("change", "#role-select", function () {
        var subjectsTaught = $("#subjects-taught")
        var roleVal = $(this).val();
        var teacher = 'Учитель';
        if (roleVal && roleVal.indexOf(teacher) !== -1) {
            subjectsTaught.show()
        } else {
            subjectsTaught.hide()
        }
    });

    // Handle the change events for copy lessons selectors
    $(".main-selector").change(function () {
        var parentDiv = $(this).closest(".selectors-group");
        var secondarySelectorDiv = parentDiv.find(".secondary-selector-div");
        if ($(this).val() === 'specific') {
            secondarySelectorDiv.show();
        } else {
            secondarySelectorDiv.hide();
        }
    });

    // Handle the change event for subject types selector
    $(".selectors-group").on("change", "#subject-type-select", function () {
        var subjectTypeVal = $(this).val();
        var classSelectRow = $("#school-class-row");
        var school = '1';

        if (subjectTypeVal && subjectTypeVal.indexOf(school) !== -1) {
            classSelectRow.show();
        } else {
            classSelectRow.hide();
        }
    });

    function formatDate(date) {
        var day = date.getDate();
        var month = date.getMonth() + 1; // Months are zero-based
        return (day < 10 ? '0' : '') + day + '.' + (month < 10 ? '0' : '') + month;
    }

    $(".datepicker-week").datepicker({
        onSelect: function (dateText, inst) {
            var selectedDate = $(this).datepicker('getDate');
            var dayOfWeek = selectedDate.getDay();

            var startOfWeek = new Date(selectedDate);
            startOfWeek.setDate(selectedDate.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));

            var endOfWeek = new Date(startOfWeek);
            endOfWeek.setDate(startOfWeek.getDate() + 6);

            var formattedStartDate = formatDate(startOfWeek);
            var formattedEndDate = formatDate(endOfWeek);

            var pContainer = $(this).closest(".selectors-group").find(".week-range")
            pContainer.html("<b>" + formattedStartDate + " - " + formattedEndDate + "</b>");

            $(this).val(dateText);
        }
    });

    // Search in select options
    function initializeSelectize(selector, plugins = [], create = false) {
        const selectizeOptions = {
            onDropdownOpen: function ($dropdown) {
                $dropdown.find('.selectize-dropdown-content').perfectScrollbar();
            },
            onDropdownClose: function ($dropdown) {
                $dropdown.find('.selectize-dropdown-content').perfectScrollbar('destroy');
            },
            plugins: plugins
        };

        if (create) {
            selectizeOptions.create = function(input) {
                return {
                    value: input,
                    text: input
                };
            };
            selectizeOptions.render = {
                option_create: function(data, escape) {
                    return '<div class="create">Добавить: <strong>' + escape(data.input) + '</strong></div>';
                }
            };
        }

        $(selector).selectize(selectizeOptions);
    }

    initializeSelectize('.select-search-add', ['remove_button'], true);

    initializeSelectize('.select-search');

    initializeSelectize('.select-search-mult', ['remove_button']);

});
