$(document).ready(function(){

    // Adjust the width of class boxes based on the width of table cells
    function adjustClassBoxWidth() {
        $('.card-content').find('.table tbody tr td').each(function() {
            var colWidth = $(this).width();
            var classBox = $(this).find('.class-box');
            classBox.width(colWidth - 10);
        });
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

    // Switch between sections in school students and subjects
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
        if ($(".timepicker-input").wickedpicker("widget").is(":visible")) {
            $(".timepicker-input").wickedpicker("hide");
        }
    });

    // Set value of wickedpicker in lesson-form
    $('.lesson-form').find('.timepicker-value').each(function() {
        var timepickerVal = $(this).val();
        var timepickerRow = $(this).closest('.row');
        if (timepickerVal) {
            timepickerRow.find('.timepicker-input').wickedpicker({now: timepickerVal});
        } else {
            timepickerRow.find('.timepicker-input').wickedpicker({now: '09 : 00'});
        }
    });

    $('.lesson-form').on("change", '.timepicker-input', function () {
        var timepickerVal = $(this).val();
        var timepickerRow = $(this).closest('.row');
        timepickerRow.find('.timepicker-value').val(timepickerVal);
    });

    $('.timepicker-input').trigger('change');

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
        var contactSelection = contactSection.find(".contact-selection");

        if (relationSelector.val() === "Другое") {
            otherRelationRow.show();
            contactInfo.show();
            contactSelection.show();
        } else if (relationSelector.val() === "Сам ребенок") {
            otherRelationRow.hide();
            contactInfo.hide();
            contactSelection.find(".contact-select").val("Добавить");
            contactSelection.find(".contact-select").trigger("change");
            contactSelection.hide();
        } else {
            otherRelationRow.hide();
            contactInfo.show();
            contactSelection.show();
        }
    });

    $(".contact-relation").trigger("change");


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
                    <div class="col-md-6">
                        <div class="form-control">${selectedPerson[0].last_name}</div>
                    </div>
                </div>
                <div class="row">
                    <label class="control-label col-md-3">Имя:</label>
                    <div class="col-md-6">
                        <div class="form-control">${selectedPerson[0].first_name}</div>
                    </div>
                </div>
                <div class="row">
                    <label class="control-label col-md-3">Отчество:</label>
                    <div class="col-md-6">
                        <div class="form-control">${selectedPerson[0].patronym}</div>
                    </div>
                </div>
            `);

            personInfoContacts.html(`
                <div class="row">
                    <label class="control-label col-md-3">Телеграм:</label>
                    <div class="col-md-6">
                        <div class="form-control">${selectedPerson[0].telegram}</div>
                    </div>
                </div>
                <div class="row">
                    <label class="control-label col-md-3">Телефон:</label>
                    <div class="col-md-6">
                        <div class="form-control">${selectedPerson[0].phone}</div>
                    </div>
                </div>
                <div class="row">
                    <label class="control-label col-md-3">Другое:</label>
                    <div class="col-md-6">
                        <div class="form-control">${selectedPerson[0].other_contact}</div>
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
            updatePersonInformation(personSelector, personSection)
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

    var contactCount = Number($("#contact-count").val());
    // Function to add a new contact section dynamically
    function addContactSection() {
        var firstContactSection = $(".contact-section").first()
        firstContactSection.find("select").each(function() {
            if ($(this)[0].selectize) {
                inputValue = $(this)[0].selectize.getValue()
                $(this)[0].selectize.destroy();
            }
        });

        var contactSection = firstContactSection.clone();

        var firstSelectizeElement = firstContactSection.find(".contact-options.select-search");
        initializeSelectize(firstSelectizeElement);
        firstSelectizeElement[0].selectize.setValue(inputValue);

        contactSection.find(".contact-relation").val("Мама");
        contactSection.find(".relation-other-row").hide();
        contactSection.find(".contact-select").val("Добавить");
        contactSection.find(".contact-options-row").hide();
        contactSection.find(".contact-input").show();
        contactSection.find(".contact-information").hide();
        var originalTitle = contactSection.find("h5").text();
        var newTitle = "Дополнительный контакт " + contactCount;
        contactSection.find("h5").text(newTitle);

        contactSection.find("select, input[type='text'], input[type='hidden']").each(function() {
            var originalName = $(this).attr("name");
            if (originalName) {
                var newName = originalName.replace("-0", "-" + contactCount);
                $(this).attr("name", newName);
            }
            var originalId = $(this).attr("id");
            if (originalId) {
                var newId = originalId.replace("-0", "-" + contactCount);
                $(this).attr("id", newId);
            }
            if ($(this).is("input[type='text']")) {
                $(this).val("");
            }
            if ($(this).is("input[type='hidden']")) {
                $(this).val("");
            }
        });

        return contactSection;
    }

    // Add a new contact section when adding a new client
    $("#add-contact-btn").click(function() {
        var newContactSection = addContactSection();
        newContactSection.appendTo("#contact-sections");

        var newSelectizeElement = newContactSection.find(".contact-options.select-search");
        initializeSelectize(newSelectizeElement);

        contactCount++;
        if (contactCount >= 2) {
            $("#remove-contact").show();
        }
    });

    // Remove last contact section when adding a new client
    $("#remove-contact").click(function() {
        $("#contact-sections .contact-section:last").remove();
        contactCount--;
        if (contactCount === 1) {
            $("#remove-contact").hide();
        }
    });

    // Function to switch between different sections based on button clicks
    function handleTabButtonClick(buttonId) {
        var targetId = '#' + buttonId.replace('-btn', '');
        $('#show-subjects, #show-contacts, #show-subscriptions, #show-after-school, #show-finances').hide();
        $(targetId).show();
    }

    // Show different sections based on button clicks
    $('#show-contacts-btn, #show-subjects-btn, #show-subscriptions-btn, #show-after-school-btn, #show-finances-btn').click(function () {
        handleTabButtonClick(this.id);
    });

    // Toggle new contact form when editing a client
    $('#show-new-contact-btn, #hide-new-contact-btn').click(function () {
        $('#show-new-contact, #new-contact-form').toggle();
    });

    // Toggle client selector based on button clicks
    $(".add-client-btn, .close-client-btn").click(function() {
        $(".add-client-btn, .add-client-form").toggle();
    });

    // Handle the change event for lesson subject selector
    $('.lesson-subjects-select').change(function () {
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
            var lessonSubjectSelector = $(this).find('.lesson-subjects-select');
            lessonSubjectSelector.trigger("change");
        });

    });

    // Handle the change event for subscription subject selector
    $('.subscription-select').change(function () {
        var subjectId = Number($(this).val());
        var selectedSubject = subscriptionSubjectsData.filter(function(subject) {
            return subject.id === subjectId;
        });

        const subscriptionTypeSelector = $('.subscription-type-select');
        subscriptionTypeSelector.empty();

        $.each(selectedSubject[0].subscription_types_info, function (index, subscriptionType) {
            subscriptionTypeSelector.append(`<option value="${index}">${subscriptionType}</option>`);
        });

        subscriptionTypeSelector.trigger("change");
    });

    $('.subscription-type-select').change(function () {
        var subscriptionType = $(this).val();
        var subjectId = Number($('.subscription-select').val());
        var selectedSubject = subscriptionSubjectsData.filter(function(subject) {
            return subject.id === subjectId;
        });
        const priceDisplay = $('.price-display');
        priceDisplay.html(`<b>${selectedSubject[0].price_info[subscriptionType]}</b>`);
    });

    // Trigger selectors change when subscription modal is shown
    $('.subscription-modal-trigger').on('click', function () {
        var subscriptionModalId = $(this).data('target');
        var subscriptionModal = $(subscriptionModalId);
        var subscriptionSubjectSelector = subscriptionModal.find('.subscription-select');
        subscriptionSubjectSelector.trigger("change");
    });

    // Function to validate date input
    function validateDateInput(validatedForm) {
        validatedForm.find('.date-input').each(function() {
            var dateInput = $(this);
            var dateValue = dateInput.val();
            var dateDiv = dateInput.closest('.date-div');
            var errorDiv = dateInput.closest('.row');
            if (dateInput.hasClass('required')) {
                var isValidDate = moment(dateValue, 'DD.MM.YYYY', true).isValid();
                if (!isValidDate) {
                    errorDiv.addClass("has-error");
                    var errorSpan = `<span class="error-span" style="color:red;">Неправильный формат даты</span>`;
                    var existingErrorSpan = dateDiv.find('.error-span');

                    if (existingErrorSpan.length === 0) {
                        dateDiv.append(errorSpan);
                    }
                } else {
                    errorDiv.removeClass("has-error");
                    dateDiv.find('.error-span').remove();
                }
            } else {
                errorDiv.removeClass("has-error");
                dateDiv.find('.error-span').remove();
            }
        });
    }

    // Function to validate date input range
    function validateDateInputRange(validatedForm) {
        var dateInput = validatedForm.find('.date-input');
        var dateDiv = dateInput.closest('.date-div');
        var errorDiv = dateInput.closest('.row');

        if (dateInput.hasClass('required')) {
            var periodValue = validatedForm.find('.period').val();
            var dateValue = dateInput.val();
            var periodParts = periodValue.split('-');
            var dateParts = dateValue.split('.');
            var isWithinPeriod = (
                parseInt(dateParts[1]) === parseInt(periodParts[0]) &&
                parseInt(dateParts[2]) === parseInt(periodParts[1])
            );
            if (!isWithinPeriod) {
                errorDiv.addClass("has-error");
                var errorSpan = `<span class="error-span" style="color:red;">Выберете дату в выбранном месяце</span>`;
                var existingErrorSpan = dateDiv.find('.error-span');

                if (existingErrorSpan.length === 0) {
                    dateDiv.append(errorSpan);
                }
            } else {
                errorDiv.removeClass("has-error");
                dateDiv.find('.error-span').remove();
            }
        } else {
            errorDiv.removeClass("has-error");
            dateDiv.find('.error-span').remove();
        }
    }

    // Function to validate time input field
    function validateTimeInput(validatedForm) {
        validatedForm.find('.time-input').each(function() {
            var timeInput = $(this);
            var timeDiv = timeInput.closest('.time-div');
            var errorDiv = timeInput.closest('.row');

            var timeValue = timeInput.val();
            var timeRegex = /^\d{1,2}\s*:\s*\d{2}$/;
            var isValidTimeFormat = timeRegex.test(timeValue);
            var [hours, minutes] = timeValue.split(':').map(val => parseInt(val.trim(), 10));
            var isInvalidTime = (hours < 0 || hours > 23 || minutes < 0 || minutes > 59);

            if (!isValidTimeFormat || isInvalidTime) {
                errorDiv.addClass("has-error");
                var errorSpan = `<span class="error-span" style="color:red;">Неправильный формат времени (ЧЧ : ММ)</span>`;
                var existingErrorSpan = timeDiv.find('.error-span');

                if (existingErrorSpan.length === 0) {
                    timeDiv.append(errorSpan);
                }
            } else {
                errorDiv.removeClass("has-error");
                timeDiv.find('.error-span').remove();
            }
        });
    }


    // Function to validate input
    function validateFieldInput(validatedForm) {
        validatedForm.find('.field-input').each(function() {
            var fieldInput = $(this);
            var fieldValue = fieldInput.val();
            var fieldDiv = fieldInput.closest('.field-div');
            var errorDiv = fieldInput.closest('.row, td');

            if (fieldInput.hasClass('required')) {
                if (!fieldValue) {
                    errorDiv.addClass("has-error");
                    var errorSpan = `<span class="error-span" style="color:red;">Заполните это поле</span>`;
                    var existingErrorSpan = fieldDiv.find('.error-span');

                    if (existingErrorSpan.length === 0) {
                        fieldDiv.append(errorSpan);
                    }
                } else {
                    errorDiv.removeClass("has-error");
                    fieldDiv.find('.error-span').remove();
                }
            } else {
                errorDiv.removeClass("has-error");
                fieldDiv.find('.error-span').remove();
            }
        });
    }

    // Function to validate password input and repeat-password field
    function validatePasswordInput(validatedForm) {
        var passwordInput = validatedForm.find('.password-input');
        var passwordValue = passwordInput.val();
        var passwordDiv = passwordInput.closest('.password-div');
        var errorDiv = passwordInput.closest('.row');

        var isValidPassword = /^(?=.*[\d])(?=.*[!@#$%^&*])[\w!@#$%^&*]{7,20}$/.test(passwordValue);

        if (!isValidPassword) {
            errorDiv.addClass("has-error");
            var errorSpan = `<span class="error-span" style="color:red;">Не менее 7 символов, латинские буквы, символы и цифры</span>`;
            var existingErrorSpan = passwordDiv.find('.error-span');

            if (existingErrorSpan.length === 0) {
                passwordDiv.append(errorSpan);
            }
        } else {
            errorDiv.removeClass("has-error");
            passwordDiv.find('.error-span').remove();
        }
    }

    // Function to validate repeat-password field
    function validateRepeatPassword(validatedForm) {
        var repeatPasswordInput = validatedForm.find('.repeat-password-input');
        var repeatPasswordValue = repeatPasswordInput.val();
        var passwordValue = validatedForm.find('.password-input').val();
        var repeatPasswordDiv = repeatPasswordInput.closest('.repeat-password-div');
        var errorDiv = repeatPasswordInput.closest('.row');

        if (passwordValue !== repeatPasswordValue) {
            errorDiv.addClass("has-error");
            var errorSpan = `<span class="error-span" style="color:red;">Пароли не совпадают</span>`;
            var existingErrorSpan = repeatPasswordDiv.find('.error-span');

            if (existingErrorSpan.length === 0) {
                repeatPasswordDiv.append(errorSpan);
            }
        } else {
            errorDiv.removeClass("has-error");
            errorDiv.find('.error-span').remove();
        }
    }

    // Validate add-user and change-password forms
    $('form.add-user-form, form.change-password-form').submit(function(event) {
        var currentForm = $(this);
        validateFieldInput(currentForm);
        validatePasswordInput(currentForm);
        validateRepeatPassword(currentForm);

        if ($(this).find('.has-error').length > 0) {
            event.preventDefault();
        }
    });

    // Validate subscription, copy-lessons, change-lessons and grade forms
    $('form.subscription-form, form.copy-lessons-form, form.change-lessons-form, form.grade-form').submit(function(event) {
        var currentForm = $(this);
        validateDateInput(currentForm);

        if ($(this).find('.has-error').length > 0) {
            event.preventDefault();
        }
    });

    // Validate forms with required field input
    $('form.finance-form, form.change-room-form, form.add-room-form, form.deposit-form, form.school-subject-form, ' +
      'form.change-class-form, form.add-class-form, form.change-subscription-form, form.add-subscription-form, ' +
      'form.change-after-school-form, form.add-after-school-form').submit(function(event) {
        var currentForm = $(this);
        validateFieldInput(currentForm);

        if ($(this).find('.has-error').length > 0) {
            event.preventDefault();
        }
    });

    // Validate add-event form
    $('form.add-event-form').submit(function(event) {
        var currentForm = $(this);
        validateTimeInput(currentForm);

        if ($(this).find('.has-error').length > 0) {
            event.preventDefault();
        }
    });

    // Validate after-school form
    $('form.after-school-form').submit(function(event) {
        var currentForm = $(this);
        validateDateInput(currentForm);
        validateFieldInput(currentForm);
        validateDateInputRange(currentForm);

        if ($(this).find('.has-error').length > 0) {
            event.preventDefault();
        }
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
    $(".employee-section, #role-select-row").on("change", ".role-select", function () {
        var subjectsTaught = $("#subjects-taught");
        var roleVal = $(this).val();
        var teacher = 'Учитель';
        if (roleVal && roleVal.indexOf(teacher) !== -1) {
            subjectsTaught.show();
        } else {
            subjectsTaught.hide();
        }
    });

    // Handle the change events for copy lessons selectors
    $(".main-selector").change(function () {
        var parentDiv = $(this).closest(".selectors-group");
        var secondarySelectorDiv = parentDiv.find(".secondary-selector-div");
        if ($(this).val() === 'specific') {
            secondarySelectorDiv.show();
            if (secondarySelectorDiv.hasClass("date-div")) {
                secondarySelectorDiv.find(".date-input").addClass("required");
            }
        } else {
            secondarySelectorDiv.hide();
            if (secondarySelectorDiv.hasClass("date-div")) {
                secondarySelectorDiv.find(".date-input").removeClass("required");
            }
        }
    });

    // Handle the change event for subject types selector
    $(".selectors-group").on("change", "#subject-type-select", function () {
        var subjectTypeVal = $(this).val();
        var classSelectRow = $("#school-class-row");
        var schoolType = $('#school-type').val();;

        if (subjectTypeVal && subjectTypeVal.indexOf(schoolType) !== -1) {
            classSelectRow.show();
        } else {
            classSelectRow.hide();
        }
    });

    // Function to format date in datepicker
    function formatDate(date) {
        var day = date.getDate();
        var month = date.getMonth() + 1;
        return (day < 10 ? '0' : '') + day + '.' + (month < 10 ? '0' : '') + month;
    }

    $(".selectors-group").on("change", ".datepicker", function() {
        var selectedDate = $(this).datepicker('getDate');
        var isValidDate = moment(selectedDate, 'DD.MM.YYYY', true).isValid();
        if (isValidDate) {
            var dayOfWeek = selectedDate.getDay();

            var startOfWeek = new Date(selectedDate);
            startOfWeek.setDate(selectedDate.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));

            var endOfWeek = new Date(startOfWeek);
            endOfWeek.setDate(startOfWeek.getDate() + 6);

            var formattedStartDate = formatDate(startOfWeek);
            var formattedEndDate = formatDate(endOfWeek);

            var weekRangeContainer = $(this).closest(".selectors-group").find(".week-range")
            weekRangeContainer.html("<b>" + formattedStartDate + " - " + formattedEndDate + "</b>");
        }
    });

    // Function to initialize search in select options
    function initializeSelectize(selector, create = false) {
        const selectizeOptions = {
            onDropdownOpen: function ($dropdown) {
                $dropdown.find('.selectize-dropdown-content').perfectScrollbar();
            },
            onDropdownClose: function ($dropdown) {
                $dropdown.find('.selectize-dropdown-content').perfectScrollbar('destroy');
            },
            plugins: ['remove_button', 'auto_position']
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

    // Search in select options with adding new options
    initializeSelectize('.select-search-add', true);

    // Search in select options without adding new options
    initializeSelectize('.select-search');


    var lessonCount = Number($("#lesson-count").val());
    // Function to add a new lesson section dynamically
    function addLessonSection() {
        var firstLessonSection = $(".lesson-section").first()
        var selectizeElements = {};
        firstLessonSection.find('select').each(function() {
            if ($(this)[0].selectize) {
                selectizeElements[$(this).attr('name')] = $(this)[0].selectize.getValue();
                $(this)[0].selectize.destroy();
            }
        });

        var lessonSection = firstLessonSection.clone();

        $.each(selectizeElements, function(key, value) {
            var selectElement = firstLessonSection.find('select[name=' + key + ']');
            initializeSelectize(selectElement);
        });

        $.each(selectizeElements, function(key, value) {
            var selectElement = firstLessonSection.find('select[name=' + key + ']');
            selectElement[0].selectize.setValue(value);
        });

        lessonSection.attr("id", "lesson-section-" + lessonCount);
        lessonSection.find(".school-class-row").hide();
        var originalTitle = lessonSection.find("h4").text();
        var newTitle = originalTitle.replace("1", lessonCount + 1);
        lessonSection.find("h4").text(newTitle);

        lessonSection.find("select, input[type='text'], input[type='hidden']").each(function() {
            var originalName = $(this).attr("name");
            if (originalName) {
                var newName = originalName.replace("-0", "-" + lessonCount);
                $(this).attr("name", newName);
                if ($(this).is("input[type='text']") || $(this).is("input[type='hidden']")) {
                    $(this).val("");
                }
            }
            var originalId = $(this).attr("id");
            if (originalId) {
                var newId = originalId.replace("-0", "-" + lessonCount);
                $(this).attr("id", newId);
            }
        });

        return lessonSection;
    }

    // Add a new lesson section when adding new lessons
    $("#add-lesson-btn").click(function() {
        var newLessonSection = addLessonSection();
        newLessonSection.appendTo("#lesson-sections");

        var newSelectElements = newLessonSection.find(".select-search");
        initializeSelectize(newSelectElements);

        newLessonSection.find(".subject-select")[0].selectize.trigger("change");

        newLessonSection.find('.timepicker-input').wickedpicker({now: '09 : 00'});
        newLessonSection.find('.timepicker-input').trigger("change");

        lessonCount++;
        if (lessonCount >= 2) {
            $("#remove-lesson-btn").show();
        }
    });

    // Remove last lesson section when adding new lessons
    $("#remove-lesson-btn").click(function() {
        $("#lesson-sections .lesson-section:last").remove();
        lessonCount--;
        if (lessonCount === 1) {
            $("#remove-lesson-btn").hide();
        }
    });

    // Pass lesson count information when submitting new lessons
    $("#submit-lesson-btn").click(function() {
        $('#lesson-count').val(lessonCount);
    });

    // Handle the change event for new lesson subject selector
    $("#lesson-sections").on("change", ".subject-select", function() {
        var selectorVal = $(this)[0].selectize.getValue();
        var subjectId = Number(selectorVal.split("-")[0]);
        var subjectTypeId = selectorVal.split("-")[1];

        var selectedSubject = subjectsData.filter(function(subject) {
            return subject.id === subjectId;
        });

        var lessonSection = $(this).closest('.lesson-section');
        var schoolClassRow = lessonSection.find('.school-class-row');
        var classesSelector = lessonSection.find('.classes-select');
        var schoolType = $('#school-type').val();

        if (subjectTypeId === schoolType) {
            classesSelector[0].selectize.clear();
            classesSelector[0].selectize.clearOptions();
            if (!$.isEmptyObject(selectedSubject[0].school_classes)) {
                $.each(selectedSubject[0].school_classes, function (index, school_class) {
                    classesSelector[0].selectize.addOption({value:index,text:school_class});
                });
                lessonSection.find('.add-classes-btn').show();
            } else {
                lessonSection.find('.add-classes-btn').trigger("click");
            }
            schoolClassRow.show();
        } else {
            schoolClassRow.hide();
        }

        var teacherSelector = lessonSection.find('.teacher-select');
        teacherSelector[0].selectize.clear();
        teacherSelector[0].selectize.clearOptions();
        if (!$.isEmptyObject(selectedSubject[0].teachers)) {
            $.each(selectedSubject[0].teachers, function (index, teacher) {
                teacherSelector[0].selectize.addOption({value:index,text:teacher});
            });
            teacherSelector[0].selectize.addItem(Object.keys(selectedSubject[0].teachers)[0]);
            lessonSection.find('.add-teachers-btn').show();
        } else {
            lessonSection.find('.add-teachers-btn').trigger("click");
        }

    });

    $("#lesson-sections").on("click", ".add-classes-btn", function() {
        var lessonSection = $(this).closest('.lesson-section');
        var classesSelector = lessonSection.find('.classes-select');
        classesSelector[0].selectize.clear();
        classesSelector[0].selectize.clearOptions();
        $.each(classesData, function (index, schoolClass) {
            var optionValue = Object.keys(schoolClass)[0]
            classesSelector[0].selectize.addOption({value:optionValue,text:schoolClass[optionValue]});
        });
        $(this).hide();
    });

    $("#lesson-sections").on("click", ".add-teachers-btn", function() {
        var lessonSection = $(this).closest('.lesson-section');
        var teacherSelector = lessonSection.find('.teacher-select');
        teacherSelector[0].selectize.clear();
        teacherSelector[0].selectize.clearOptions();
        $.each(teachersData, function (index, teacher) {
            var optionValue = Object.keys(teacher)[0]
            teacherSelector[0].selectize.addOption({value:optionValue,text:teacher[optionValue]});
        });
        teacherSelector[0].selectize.addItem(Object.keys(teachersData[0])[0]);
        $(this).hide();
    });

    var subjectSelect = $(".subject-select").eq(0);

    if (subjectSelect.length && subjectSelect[0].selectize) {
        subjectSelect[0].selectize.trigger("change");
    }

    $(".float-field").change(function() {
        $(this).val(parseFloat($(this).val()).toFixed(1));
    });

    $(".price_row, .subscription-row").on("change", "input[type='checkbox']", function() {
        var parentRow = $(this).closest(".price_row, .subscription-row")
        if (this.checked) {
            parentRow.find(".optional-field").hide();
        } else {
            parentRow.find(".optional-field").show();
        }
    });

    $("input[type='checkbox']").trigger("change");

    // Add subscription type
    $("#subscription-types-container").on("change", "#add-subscription-type", function() {
        var subscriptionTypeCount = Number($("#subscription-type-count").val());
        var selectorVal = $(this).val();
        var selectorText = $("option:selected", this ).text();
        $("option:selected", this ).remove()
        $("option:first", this).prop('selected', true);
        if (subscriptionTypeCount !== 0) {
            var newSubscriptionTypeRow = $(".subscription-type").first().clone();
            newSubscriptionTypeRow.find("label").empty();
            newSubscriptionTypeRow.find("p").html(selectorText);
            newSubscriptionTypeRow.find(".subscription-type-value").val(selectorVal);
            newSubscriptionTypeRow.appendTo("#subscription-types");
        } else {
            newSubscriptionTypeRow = $("#no-subscription-types").clone();
            newSubscriptionTypeRow.addClass("subscription-type").removeAttr('id');
            newSubscriptionTypeRow.find("p").html(selectorText);
            var newSubscriptionTypeHTML = `
                <div class="col-md-1">
                    <button type="button" class="btn btn-danger del-btn-sm delete-subscription">Удалить</button>
                </div>
                <input type="hidden" name="subscription_types" class="subscription-type-value" value="${selectorVal}">`;
            $(newSubscriptionTypeHTML).appendTo(newSubscriptionTypeRow);
            $("#subscription-types").append(newSubscriptionTypeRow);
            $("#no-subscription-types, #subscription-types").toggle();
        }
        $("#subscription-type-count").val(subscriptionTypeCount + 1);
    });

    // Delete subscription type
    $("#subscription-types-container").on("click", ".delete-subscription", function() {
        var subscriptionTypeRow = $(this).closest(".subscription-type");
        subscriptionTypeText = subscriptionTypeRow.find("p").html();
        subscriptionTypeVal = subscriptionTypeRow.find(".subscription-type-value").val();
        var optionHTML = `
            <option value="${subscriptionTypeVal}">${subscriptionTypeText}</option>`;
        $('#add-subscription-type').append(optionHTML);
        subscriptionTypeRow.remove();
        var subscriptionTypeCount = Number($("#subscription-type-count").val()) - 1;
        $("#subscription-type-count").val(subscriptionTypeCount);
        if (subscriptionTypeCount === 0) {
            $("#no-subscription-types, #subscription-types").toggle();
        }

    });

    // Delete employee role
    $(".employee-role").on("click", ".delete-role", function() {
        var roleRow = $(this).closest(".employee-role");
        employeeRole = roleRow.find(".role-value").val();
        $("#role-select")[0].selectize.addOption({value:employeeRole,text:employeeRole});
        roleRow.remove();
        if (employeeRole === "Учитель") {
            $("#teacher-subjects-section").remove();
        }
    });

    // Delete teacher subject
    $("#subjects-row").on("click", ".delete-subject", function() {
        var subjectRow = $(this).closest(".subjects-row");
        teacherSubjectVal = subjectRow.find(".subject-value").val();
        teacherSubjectText = subjectRow.find("p").html();
        $("#subject-select")[0].selectize.addOption({value:teacherSubjectVal,text:teacherSubjectText});
        subjectRow.remove();
    });

    // Create list of student grades in the grade-modal
    $("#grade-modal, #final-grade-modal").on("click", ".add-grad-btn", function () {
        var gradeForm = $(this).closest(".grade-form");
        var selectedStudent = gradeForm.find(".student-select option:selected");
        if (selectedStudent.length > 0) {
            var studentId = selectedStudent.val();
            var studentName = selectedStudent.text();
            var grade = gradeForm.find(".student-grade").val();
            var comment = gradeForm.find(".student-comment").val();
            if (grade || comment) {
                var studentGradeText = studentName + ": " + grade + " - " + comment;
                var gradeInputName = "new_grade_" + studentId;
                var commentInputName = "new_comment_" + studentId;
                selectedStudent.remove();

                var studentGradeRow = `
                    <div class="student-grade-row">${studentGradeText}<a href="#" class="delete-grade" data-student="${studentId}">×</a></div>`;

                var studentInput = `
                    <div id="input-${studentId}">
                        <input type="hidden" name="${gradeInputName}" value="${grade}">
                        <input type="hidden" name="${commentInputName}" value="${comment}">
                    </div>`;
                gradeForm.find(".grades-container").append(studentGradeRow);
                gradeForm.find(".input-container").append(studentInput);

                $(".student-comment").val('');
            }
        }
    });

    // Save original options of student selector
    var originalOptions = $(".student-select option").clone();

    // Refresh the grade-modal when closing it
    $("#grade-modal, #final-grade-modal").on("hidden.bs.modal", function () {
        $(".grades-container").empty();
        $(".input-container").empty();
        $(".student-select option").remove();
        $(".student-select").append(originalOptions);
    });

    // Delete student's grade from the list of grades
    $(".grades-container").on("click", ".delete-grade", function (e) {
        e.preventDefault();
        var gradeForm = $(this).closest(".grade-form");
        var studentId = String($(this).data("student"));
        $(this).parent().remove();
        var restoreOption = originalOptions.filter(function() {
            return $(this).val() === studentId;
        });
        if (restoreOption.length > 0){
            gradeForm.find(".student-select").append(restoreOption);
        }

        $(".#input-" + studentId).remove();
    });

    // Handle change of grade change-mode selector
    $("#change-grade-modal").on("change", ".change_mode_select", function () {
        var changeMode = $(this).val();
        if (changeMode === 'delete') {
            $(".change-grade-row").hide();
        } else {
            $(".change-grade-row").show();
        }
    });

    // Handle term selector change when adding after-school student
    $("#after-school-modal").on("change", ".term-selector", function () {
        term = $(this).val();
        if (term === "month") {
            $(".shift-row").show();
            $(".hours-row, .day-row").hide();
            $(".day-row").find(".date-input").removeClass("required");
        } else if (term === "day") {
            $(".shift-row, .hours-row").hide();
            $(".day-row").show();
            $(".day-row").find(".date-input").addClass("required");
        } else {
            $(".shift-row").hide();
            $(".hours-row, .day-row").show();
            $(".hour-number").val(1);
            $(".hours-row").find(".field-input").addClass("required");
            $(".day-row").find(".date-input").addClass("required");
        }
        var prices = afterSchoolPrices.filter(function(price) {
            return price.period === term;
        });
        $(".price-selector").empty();
        $.each(prices, function (i, price) {
            $('.price-selector').append($('<option>', {
                value: price.id,
                text : price.price + " Лари"
            }));
        });
    });

    // Recount price by changing number of hours
    $(".hour-number").on("input", function() {
        factor = Number($(this).val());
        if (factor >= 1 && factor <= 4) {
            var prices = afterSchoolPrices.filter(function(price) {
                return price.period === term;
            });
            $(".price-selector").empty();
            $.each(prices, function (i, price) {
                $('.price-selector').append($('<option>', {
                    value: price.id,
                    text : price.price*factor + " Лари"
                }));
            });
        }
    });

    // Trigger term selector on open after-school-modal
    $("#after-school-modal").on('shown.bs.modal', function () {
        $(".term-selector").trigger("change");
    });

    // Switch between main-teacher div and main-teacher form
    $(".main-teacher-btn").on("click", function() {
        $(".main-teacher, .main-teacher-form").toggle();
    });


    $('#school-class-select').on('change', function() {
        var schoolClass = $('#school_class').val()
        var selectorVal = $(this).val();
        if (selectorVal.indexOf(schoolClass) === -1) {
            $(this)[0].selectize.addItem(schoolClass);
        }
    });

});
