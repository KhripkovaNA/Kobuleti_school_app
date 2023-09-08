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

    var contactCount = 1;
    function addContactSection() {
        var contactSection = $(".contact-section").first().clone();
        contactSection.find(".contact-radio").prop("checked", false);
        contactCount++;
        contactSection.attr("id", "contact-section-" + contactCount);
        contactSection.find("select, input[type='text']").each(function() {
            var originalName = $(this).attr("name");
            var newName = originalName.replace("_1", "_" + contactCount);
            $(this).attr("name", newName).val("");
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
        console.log(contactCount);
        }
    });

    $(".contact-section").each(function () {
        const relationSelector = $(this).find(".contact-relation");
        const otherRelationRow = $(this).find(".relation-other-row");
        const contactInfoDiv = $("#contact-info");

        relationSelector.on("change", function () {
            if (relationSelector.val() === "Другое") {
                otherRelationRow.show();
                contactInfoDiv.show();
            } else if (relationSelector.val() === "Сам ребенок") {
                otherRelationRow.hide();
                contactInfoDiv.hide();
            } else {
                otherRelationRow.hide();
                contactInfoDiv.show();
            }
        });
    });

    $("#remove-contact").click(function() {
        $("#contact-sections .contact-section:last").remove();
        contactCount--;
        if (contactCount === 1) {
            $("#remove-contact").hide();
        console.log(contactCount);
        }
    });

    $("#submit-btn").click(function() {
        $('#contact-count').val(contactCount);
    });
});

