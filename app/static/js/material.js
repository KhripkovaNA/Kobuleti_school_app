$(document).ready(function(){
    $("#toggle-sidebar").click(function(){
      if ($(".sidebar").is(":visible")) {
        $(".sidebar").hide();
        $(".main-panel").css("width", "100%");
      } else {
        $(".sidebar").show();
        $(".main-panel").css("width", "calc(100% - 260px)");
      }
    });

    $('.sidebar .sidebar-wrapper, .main-panel, .scroll-table').perfectScrollbar();
    $('.scroll-table-body').perfectScrollbar({
        suppressScrollX: true
    });

    $.datepicker.setDefaults( $.datepicker.regional[ "ru" ] );
    $(".datepicker").datepicker({
        dateFormat: "dd.mm.yy",
        changeYear: true,
    });

    $(".main-panel").on("scroll", function() {
        if ($(".datepicker").datepicker("widget").is(":visible")) {
            $(".datepicker").datepicker("hide");
        }
    });

    $("#status-select").on("change", function () {
        const selectedStatus = $(this).val();
        const pauseDate = $("#pause-date");
        const leavingReason = $("#leaving-reason");

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
    });

    $("#status-select").trigger("change");

    var contactCount = 1;
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

    $("#add-contact-btn").click(function() {
        var newContactSection = addContactSection();
        newContactSection.appendTo("#contact-sections");
        if (contactCount >= 2) {
            $("#remove-contact").show();
        }
    });

    $("#contact-sections").on("change", ".contact-relation", function () {
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

    $(".contact-relation").trigger("change");

    $("#contact-sections").on("change", ".contact-select", function () {
        var contactSelector = $(this);
        var contactSection = contactSelector.closest(".contact-section");
        var contactOptionsRow = contactSection.find(".contact-options-row");
        var contactInformation = contactSection.find(".contact-information")

        if (contactSelector.val() === "Добавить") {
            contactInformation.show();
            contactOptionsRow.hide();
        } else {
            contactInformation.hide();
            contactOptionsRow.show();
        }
    });

    $(".contact-select").trigger("change");

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
});

