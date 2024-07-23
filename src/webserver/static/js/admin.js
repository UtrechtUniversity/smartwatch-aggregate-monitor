// https://www.jonthornton.com/jquery-timepicker/
// https://github.com/jonthornton/jquery-timepicker#timepicker-plugin-for-jquery
var id = 1
var Highlights = []
var mask = '*****'

class Highlight {
    constructor(id, date, timestamp, label) {
        this.date = date;
        this.timestamp = timestamp;
        this.label = label;
        this.id = id;
    }
}

function formatSeconds(sec) {
    var d = Math.floor(sec / (3600*24))
    var h = Math.floor(sec % (3600*24) / 3600)
    var m = Math.floor(sec % 3600 / 60)
    var s = Math.floor(sec % 60)
    return (d>0?d+"d":"")+(h>0?h+"u":"")+(m>0?m+"m":"")+(s>0?s+"s":"")
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
    Highlights.push(new Highlight(id++, $("#today").val(), formatStartTime(new Date()), label))
    postData({'highlights': Highlights});
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
    
    devices.push({'id':'avg', 'serial':'', 'password': '', 'latest_request': '' })
    devices.forEach((x, i) => {
        if (x.has_data || x.id=='avg')
            data_link = `<a href="/device/${x.id}/" target="window_${x.id}">&#128269;</a>`
        else
            data_link = '(no&nbsp;data)'

        let img_path = image_base_url.replace('__ID__', x.id)
        var req_diff = ''
        if (x.latest_request) req_diff = ` (${formatSeconds(Math.round((new Date() - new Date(x.latest_request))/1000))})`
        
        line =
            `<tr>` +
                `<td>${x.id}</td>`+
                `<td>${x.serial}</td>`+
                `<td data-pass="${x.password}" class="pointable" id="p${x.id}" onmousedown="showPass(this)">${mask}</td>`+
                `<td>${x.latest_request}<span class="small">${req_diff}</span></td>`+
                `<td class="center small">${data_link}</td>`+
                `<td class="center small code">`+
                    `<span class="pointable qr-link" data-id="${x.id}" onmousedown="showCode(this)">(klik)</span>`+
                    `<span class="pointable qr-code" data-id="${x.id}" onmousedown="showCode(this)">` +
                        `(sluiten)<br />` +
                        `<object type="image/svg+xml" data="${img_path}" class="logo">QR code</object>`+
                    `</span>` +
                `</td>`+
            `</tr>`;
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

function showCode(ele) {
    let a = $(ele).attr('data-id')
    $('.qr-link[data-id='+a+']').toggle();
    $('.qr-code[data-id='+a+']').toggle();
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
            // console.log(data);
            setData(data);
        }
    });
}

function setSomeTime(time, event) {
    if (time) {
        var obj = {};
        obj[event] = formatStartTime(time, false);
        postData(obj)
    }
}

function setData(data) {
    showDevices(data.devices);
    Highlights = []
    data.highlights.forEach((x, i) => {
        Highlights.push(new Highlight(x.id, x.date, x.timestamp, x.label));
    })
    showHighlights();
    $('#showGraphs').prop('checked', data.show_graphs)
    // $('#data_dir').html(data.data_dir)
    $("#startTime").html(data.session.start);
    $("#endTime").html(data.session.end);
    $("#today").val(data.session.today);
}

function loadData() {
    $("#load-status").html("&#10227;").show();
    $.getJSON(data_url, function(data) {
        setData(data)
        $("#load-status").fadeOut(555);
    }); 
    setTimeout("loadData()", data_reload);
}

function exportHighlights() {
    const blob = new Blob([csvmaker(Highlights)], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `lowlands-session-highlights--${new Date().toISOString()}.csv`;
    a.click();    
}

function csvmaker(data) {
    csvRows = [];
    const headers = Object.keys(data[0]);
    csvRows.push(headers.join(','));
    data.forEach((x, i)=>{
        let values = Object.values(x).join(',');
        csvRows.push(values)    
    })
    return csvRows.join('\n')
}
