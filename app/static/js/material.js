$(document).ready(function(){
    adjustClassBoxWidth();

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

    $(window).resize(function () {
        adjustClassBoxWidth();
    });

    // Adjust the width of class boxes based on the width of table cells
    function adjustClassBoxWidth() {
        var tdWidth = $('.table td').width();
        var classBoxWidth = tdWidth - 10;
        $('.class-box').width(classBoxWidth);
    }

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

    // Comment submitting to the database
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

    $("#status-select").on("change", function () {
        handleStatusChange($(this), "#pause-date", "#leaving-reason");
    });

    $("#status-select-adult").on("change", function () {
        handleStatusChange($(this), "#pause-date-adult", "#leaving-reason-adult");
    });

    $("#status-select").trigger("change");

    //  ------  var contactCount = $(".contact-section").length; -----  //
    // Function to add a new contact section
    var contactCount = 1
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

    $("#contact-sections, #show-contacts").on("change", ".contact-options", function() {
        updateClientInformation($(this), ".contact-section");
    });

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

    $(".client-section").on("change", ".client-options", function() {
        updateClientInformation($(this), ".client-section");
    });

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

    $("#add-contact-btn").click(function() {
        var newContactSection = addContactSection();
        newContactSection.appendTo("#contact-sections");
        if (contactCount >= 2) {
            $("#remove-contact").show();
        }
    });

    $("#remove-contact").click(function() {
        $("#contact-sections .contact-section:last").remove();
        contactCount--;
        if (contactCount === 1) {
            $("#remove-contact").hide();
        }
    });

    $("#submit-btn").click(function() {
        $('#contact-count').val(contactCount);
    });

    $('#show-contacts-btn').click(function () {
        $('#show-subjects, #show-subscriptions').hide();
        $('#show-contacts').show();
    });

    $('#show-subjects-btn').click(function () {
        $('#show-contacts, #show-subscriptions').hide();
        $('#show-subjects').show();
    });

    $('#show-subscriptions-btn').click(function () {
        $('#show-subjects, #show-contacts').hide();
        $('#show-subscriptions').show();
    });

    $('#show-new-contact-btn, #hide-new-contact-btn').click(function () {
        $('#show-new-contact, #new-contact-form').toggle();
    });

    $(".change_contact_btn").click(function() {
        var containerNumber = $(this).closest(".form-group").attr("id").split("-").pop();
        var containerId = "#contact-info-" + containerNumber;
        var formId = "#contact-form-" + containerNumber;

        $(containerId).hide();
        $(formId).show();
    });

    $(".cancel_form_btn").click(function() {
        event.preventDefault();

        var containerNumber = $(this).closest(".login-form").attr("id").split("-").pop();
        var formId = "#contact-form-" + containerNumber;
        var containerId = "#contact-info-" + containerNumber;

        $(formId).hide();
        $(containerId).show();
    });

    $("#add-client-btn").click(function() {
        $("#clientSelector").show();
        $("#add-client-btn").hide();
    });

    $("#cancel-add-client-btn").click(function() {
        $("#add-client-btn").show();
        $("#clientSelector").hide();
    });

    window.showDropdown = function(objectId, event) {
        $('.dropdown-content').hide();
        $(`#dropdown-${objectId}`).toggle().css({
            top: event.offsetY,
            left: event.offsetX
        });
        event.stopPropagation();
    }

    $(document).on('click', function () {
        $('.dropdown-content').hide();
    });

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

});

