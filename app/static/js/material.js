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
    $('.sidebar .sidebar-wrapper, .main-panel, .scroll-table, .scroll-timetable').perfectScrollbar();
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

    // Handle the change event for the status select dropdown when adding or editing a new client
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

    // Handle status select changing for adults
    $("#status-select-adult").on("change", function () {
        handleStatusChange($(this), "#pause-date-adult", "#leaving-reason-adult");
    });

    $("#status-select").trigger("change");

    var contactCount = 1
    // Function to add a new contact section dynamically
    function addContactSection() {
        contactCount++;
        var contactSection = $(".contact-section").first().clone();
        contactSection.find(".contact-radio").prop("checked", false);
        contactSection.attr("id", "contact-section-" + contactCount);
        contactSection.find(".contact-relation").val("Мама");
        contactSection.find(".relation-other-row").hide();
        contactSection.find(".contact-select").val("Добавить");
        contactSection.find(".contact-options-row").hide();
        contactSection.find(".contact-info").show();
        contactSection.find("select, input[type='text']").each(function() {
            var originalName = $(this).attr("name");
            var newName = originalName.replace("_1", "_" + contactCount);
            $(this).attr("name", newName);
            if ($(this).is("input[type='text']")) {
                $(this).val("");
            }
        });
        contactSection.find("input[type='radio']").each(function() {
            var originalValue = $(this).val();
            var newValue = originalValue.replace("_1", "_" + contactCount);
            $(this).val(newValue);
        });
        return contactSection;
    }

    // Handle the change event for the relation select dropdown when adding or editing a new client
    $("#contact-sections, #show-contacts").on("change", ".contact-relation", function () {
        var relationSelector = $(this);
        var contactSection = relationSelector.closest(".contact-section");
        var otherRelationRow = contactSection.find(".relation-other-row");
        var contactInfoDiv = contactSection.find(".contact-info");
        var contactSelection = contactSection.find(".contact_selection")

        if (relationSelector.val() === "Другое") {
            otherRelationRow.show();
            contactInfoDiv.show();
            contactSelection.show();
        } else if (relationSelector.val() === "Сам ребенок") {
            otherRelationRow.hide();
            contactInfoDiv.hide();
            contactSelection.hide();
        } else {
            otherRelationRow.hide();
            contactInfoDiv.show();
            contactSelection.show();
        }
    });

    // Function to update client information when adding or editing a new client
    function updateClientInformation(selector, section) {
        var clientId = Number(selector.val());
        var selectedClient = clientsData.filter(function(client) {
            return client.id === clientId;
        });
        var selectedSection = selector.closest(section);

        selectedSection.find(".client-info-basic").html(`
            <div class="form-group" style="margin-top: 12px;">
                <div class="row">
                    <label class="control-label col-md-3">Фамилия:</label>
                    <div class="col-md-5">
                        <p>${selectedClient[0].last_name}</p>
                    </div>
                </div>
                <div class="row">
                    <label class="control-label col-md-3">Имя:</label>
                    <div class="col-md-5">
                        <p>${selectedClient[0].first_name}</p>
                    </div>
                </div>
                <div class="row">
                    <label class="control-label col-md-3">Отчество:</label>
                    <div class="col-md-5">
                        <p>${selectedClient[0].patronym}</p>
                    </div>
                </div>
            </div>
        `);
        selectedSection.find(".client-info-contacts").html(`
            <div class="form-group" style="margin-top: 12px;">
                <div class="row">
                    <label class="control-label col-md-3">Телеграм:</label>
                    <div class="col-md-3">
                        <p>${selectedClient[0].telegram}</p>
                    </div>
                </div>
                <div class="row">
                    <label class="control-label col-md-3">Телефон:</label>
                    <div class="col-md-3">
                        <p>${selectedClient[0].phone}</p>
                    </div>
                </div>
                <div class="row">
                    <label class="control-label col-md-3">Другое:</label>
                    <div class="col-md-3">
                        <p>${selectedClient[0].other_contact}</p>
                    </div>
                </div>
            </div>
        `);
    }

    // Update contact information based on selected person
    $("#contact-sections, #show-contacts").on("change", ".contact-options", function() {
        updateClientInformation($(this), ".contact-section");
    });

    // Handle the change event for selection between adding a new contact and choosing existing
    $("#contact-sections, #show-contacts").on("change", ".contact-select", function () {
        var contactSelector = $(this);
        var contactSection = contactSelector.closest(".contact-section");
        var contactOptionsRow = contactSection.find(".contact-options-row");
        var contactInformation = contactSection.find(".contact-information");
        var clientInformation = contactSection.find(".client-information");

        if (contactSelector.val() === "Добавить") {
            contactInformation.show();
            contactOptionsRow.hide();
            clientInformation.hide();
        } else {
            contactInformation.hide();
            contactOptionsRow.show();
            clientInformation.show();
            $(".contact-options").trigger("change");
        }
    });

    $(".contact-select").trigger("change");

    // Update client information based on selected person
    $(".client-section").on("change", ".client-options", function() {
        updateClientInformation($(this), ".client-section");
    });

    // Handle the change event for selection between adding a new client and choosing existing
    $(".client-section").on("change", ".client-select", function () {
        var clientSelector = $(this);
        var clientSection = clientSelector.closest(".client-section");
        var clientOptionsRow = clientSection.find(".client-options-row");
        var clientInput = clientSection.find(".client-input");
        var clientInformation = clientSection.find(".client-information");

        if (clientSelector.val() === "Добавить") {
            clientInput.show();
            clientOptionsRow.hide();
            clientInformation.hide();
        } else {
            clientInput.hide();
            clientOptionsRow.show();
            clientInformation.show();
            $(".client-options").trigger("change");
        }
    });

    $(".client-select").trigger("change");

    // Add a new contact form when adding a new client
    $("#add-contact-btn").click(function() {
        var newContactSection = addContactSection();
        newContactSection.appendTo("#contact-sections");
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

//    $('#show-contacts-btn').click(function () {
//        $('#show-subjects, #show-subscriptions').hide();
//        $('#show-contacts').show();
//    });
//
//    $('#show-subjects-btn').click(function () {
//        $('#show-contacts, #show-subscriptions').hide();
//        $('#show-subjects').show();
//    });
//
//    $('#show-subscriptions-btn').click(function () {
//        $('#show-subjects, #show-contacts').hide();
//        $('#show-subscriptions').show();
//    });

    // Toggle new contact form when editing a client
    $('#show-new-contact-btn, #hide-new-contact-btn').click(function () {
        $('#show-new-contact, #new-contact-form').toggle();
    });

    // Toggle client selector based on button clicks
    $("#add-client-btn, #cancel-add-client-btn").click(function() {
        $("#clientSelector, #add-client-btn").toggle();
    });

//    $("#add-client-btn").click(function() {
//        $("#clientSelector").show();
//        $("#add-client-btn").hide();
//    });
//
//    $("#cancel-add-client-btn").click(function() {
//        $("#add-client-btn").show();
//        $("#clientSelector").hide();
//    });

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

    // Handle the change event for subject types selector
    $("#subject-type-select").on("change", function () {
        const selectedType = $(this).val();
        const classSelect = $("select[name='school_classes']");
        const classSelectRow = $("#school-class-row");

        if (selectedType === "1") {
            classSelectRow.show();
        } else {
            classSelectRow.hide();
            classSelect.val(null);
        }
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

});
