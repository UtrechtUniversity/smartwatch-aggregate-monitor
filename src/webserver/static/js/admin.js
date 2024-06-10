// https://www.jonthornton.com/jquery-timepicker/
// https://github.com/jonthornton/jquery-timepicker#timepicker-plugin-for-jquery
var id = 1
var Highlights = []
var mask = '*****'

class Highlight {
    constructor(id, timestamp, label) {
        this.timestamp = timestamp;
        this.label = label;
        this.id = id;
    }
}

function htmlDecode(input) {
    var doc = new DOMParser().parseFromString(input, "text/html");
    return doc.documentElement.textContent;
}    

function deleteHighlight(id) {    
    var del = -1
    var label = ''
    Highlights.forEach((x, i) => {
        if (x.id==id) {
            del = i;
            label = x.label
        }
    })
    if (del>-1 && window.confirm(htmlDecode(`"${label}" verwijderen?`))){
        Highlights.splice(del, 1);
        postData({'highlights': Highlights});
    }
}

function markHighlight(label) {
    if (label=='') return;
    Highlights.push(new Highlight(id++, formatStartTime(new Date()), label))
}

function showHighlights() {
    var buffer = ''
    Highlights.forEach((x, i) => {
        line =
            `<tr>` +
                `<td class="right">${x.id}.</td>`+
                `<td>${x.timestamp}</td>`+
                `<td>${x.label}</td>`+
                `<td class="remove" onclick='deleteHighlight(${x.id});showHighlights();'>&#10060;</td>`+
            `</tr>
            `;
        buffer = `${buffer}${line}`
    });
    $('#highlight-list').html(buffer);
}

function showDevices(devices) {
    var buffer = ''
    passwords = []
    devices.forEach((x, i) => {
        if (x.has_data)
            data_link = `<a href="/device/${x.id}" target="window_${x.id}">&#128269;</a>`
        else
            data_link = '(no data)'
        
        line =
            `<tr>` +
                `<td>${x.id}</td>`+
                `<td>${x.serial}</td>`+
                `<td data-pass="${x.password}" class="pointable" id="p${x.id}" onmousedown="showPass(this)">${mask}</td>`+
                `<td>${x.latest_request}</td>`+
                `<td class="center">${data_link}</td>`+
            `</tr>
            `;
        buffer = `${buffer}${line}`
    });
    $('#device-list').html(buffer);
}

function showPass(ele) {
    let a = $(ele).html()
    let b = $(ele).attr('data-pass')
    $(ele).html(b)
    $(ele).attr('data-pass', a)
}

function formatStartTime(start_time, incl_seconds=true) {
    let hhmm = `${start_time.getHours()}:${(start_time.getMinutes() < 10 ? '0' : '') + start_time.getMinutes()}`
    let ss = `:${(start_time.getSeconds() < 10 ? '0' : '') + start_time.getSeconds()}`
    if (incl_seconds) {
        return `${hhmm}${ss}`
    }
    return `${hhmm}`
}

function postData(data) {
    $.ajax({
        url: "/ajax/",
        type: "POST",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function(data, textStatus, jqXHR)
        {
            // console.log(data)
        }
    });
}

function setSomeTime(time, event, id) {
    if (time) {
        $(id).html(formatStartTime(time, false));
        var obj = {};
        obj[event] = formatStartTime(time, false);
        postData(obj)
        // console.log(event, time);
    }
}

function loadData() {
    $("#load-status").html("&#10227;").show();
    $.getJSON(data_url,
        function(data)
        {
            console.log(data);
            showDevices(data.devices);
            Highlights = []
            data.highlights.forEach((x, i) => {
                Highlights.push(new Highlight(x.id, x.timestamp,x.label));
            })
            showHighlights();
            $('#showGraphs').prop('checked', data.show_graphs)
            // $('#data_dir').html(data.data_dir)
            $("#startTime").html(data.session.start);
            $("#endTime").html(data.session.end);
            $("#today").val(data.session.today);
            $("#load-status").fadeOut(555);
        }); 
    setTimeout("loadData()", data_reload);
}

function exportHighlights() {
    var csvContent = "data:text/csv;charset=utf-8," 
    Highlights.forEach((x,i)=> {
        console.log(x,i);
        csvContent = csvContent + `"${x.timestamp}","${x.label}"\n`;
    })    
    window.open(encodeURI(csvContent));
}