var eda_div = null
var pulse_div = null
var eda_text_div = null
var pulse_text_div = null

var reloads = 0
var show_graphs = false

function makePlot(p) {
    data = p.data ? p.data : []
    highlights = p.highlights ? p.highlights : {'labels': [], 'timestamps': []}
    colors = p.colors
    axis = p.axis
    titles = p.titles
    avg_only = p.avg_only

    let values = data.map(({ value }) => value).concat(data.map(({ average }) => average))
    let min = Math.min.apply(null, values),
        max = Math.max.apply(null, values)
    const fract = 1/10
    let lowest = +(min-((min+max)*fract))
    let highest = +(max+((min+max)*fract))

    let x_first = data.length>0 ? data[0].timestamp : null
    let x_last = data.length>0 ? data[data.length-1].timestamp : null

    let scaffolding = {
        marginTop: 42,
        marginRight: 27,
        marginBottom: 59,
        marginLeft: 39,
        grid: true,
        inset: -10,
    }

    if (show_graphs) {
        let marks = [
            Plot.text(['\u2015 gemiddelde'], {x: x_last, frameAnchor: "Top", fill: colors.average, fontSize:12, dx: -60, dy: -15}),
            Plot.line(data, {
                x: "timestamp",
                y: "average",
                curve: "natural",
                stroke: colors.average,
                marker: "circle"}),
            Plot.text(highlights.labels,
                {
                    textAnchor: "start",
                    frameAnchor: "top",
                    rotate: 90,
                    lineHeight: 1.5,
                    fontSize: 13,
                    fill: "black",
                    x: highlights.timestamps,
                }),
            Plot.ruleX(highlights.timestamps, {stroke: "red"}),
        ]

        if (!avg_only) {
            marks.push(Plot.text(['\u2015 jouw waarden'], {x: x_last, frameAnchor: "Top", fill: colors.value, fontSize:12, dx: -54, dy: -32}))
            marks.push(Plot.line(data, {
                x: "timestamp",
                y: "value",
                curve: "natural",
                stroke: colors.value,
                marker: "circle"}))
        }
        
        var plot_data = {
            title: titles.title, 
            // subtitle: `${titles.subtitle} ${titles.symbol}`,
            // caption: titles.caption,
            subtitle: `${titles.index} ${titles.subtitle}`,
            x: {type: "time", label: axis.x, grid: false},
            y: {label: axis.y, grid: true, domain: [lowest, highest],},
            marks: marks
        }
    } else {
        var plot_data = {
            height: 500,
            marks: [
                Plot.frame({rx: 10, ry: 10, stroke: "#999"}),
                Plot.text(["Tot straks!"], {frameAnchor: "top", fontSize: 36, fill: "#666", dy:90}),
                Plot.text([`Hier wordt na afloop van de sessie\njouw ${titles.subtitle.toLowerCase()} getoond.`],
                    {frameAnchor: "top", fontSize: 18, fill: "#666", dy: 150, lineHeight: 1.2})
            ]
        }
    }

    let plot = {...scaffolding, ...plot_data};

    return Plot.plot(plot)
}

function makePlots(data) {

    if (data.avg_only) {
        show_graphs = true;
        $("#main-title").html('Alleen gemiddelden');
        colors_eda = { average: "green" }
        colors_pulse = { average: "green"}
    } else {
        $("#main-title").html($("#main-title").attr('data-text'));
        colors_eda = { value: "red", average: "green" }
        colors_pulse = { value: "blue", average: "green"}
    }

    eda_div.innerHTML = '';
    eda_div.append(makePlot({
        data: data.session_data.eda,
        highlights: data.highlights,
        colors: colors_eda,
        axis: { x: "Time", y: "microSiemens (μS)" },
        // titles: { subtitle: "Electrodermal Activity", caption: "Fig 1. This is the EDA during the session", symbol: "\u23E6" },
        titles: { index: "Grafiek 1:", subtitle: "Huidgeleiding" },
        avg_only: data.avg_only
        }));

    eda_text_div.innerHTML = '';
    if (show_graphs)
        eda_text_div.innerHTML = 
            'Huidgeleiding (of zweetafgifte) is een maat voor hoe je huid reageert op spanning of opwinding. Je huid heeft kleine zweetklieren die zweet afscheiden. Doordat zweet elektriciteit geleidt, kan elektrische geleiding van de huid gemeten worden en krijg je een kijkje in iemands emotionele toestand.'

    pulse_div.innerHTML = '';
    pulse_div.append(makePlot({
        data: data.session_data.pulse_rate,
        highlights: data.highlights,
        colors: colors_pulse,
        axis: { x: "Time", y: "Beats per minute" },
        // titles: { subtitle: "Pulse rate", caption: "Fig 2. This is the pulse rate during the session", symbol: "\u2661" },
        titles: { index: "Grafiek 2:", subtitle: "Hartslag" },
        avg_only: data.avg_only
    }));
    pulse_text_div.innerHTML = '';
    if (show_graphs)
        pulse_text_div.innerHTML = 
            'Hartslag is het aantal keer dat je hart per minuut klopt. Je hart pompt bloed door je lichaam, en dit gebeurt sneller of langzamer afhankelijk van wat je doet en hoe je je voelt.'
}

function loadData() {
    $("#load-status").html("&#10227;").show();
    $.getJSON(data_url, function(data)
    {
        show_graphs = data.show_graphs
        for (var prop in data.session_data) {
            if (data.session_data.hasOwnProperty(prop)) {
                for (ele in data.session_data[prop]) {
                    data.session_data[prop][ele].timestamp = new Date(data.session_data[prop][ele].timestamp);
                }
            }                    
        }

        let session_start = new Date(`${data.session.today} ${data.session.start}`)
        let session_end = new Date(`${data.session.today} ${data.session.end}`)

        data.highlights.forEach(function(x,i) {
            x.timestamp = new Date(x.timestamp)
            if (x.timestamp<session_start || x.timestamp>session_end) {
                data.highlights.splice(i, 1);
            }
        })

        data.highlights = {
            'labels': data.highlights.map(({ label }) => label),
            'timestamps': data.highlights.map(({ timestamp }) => timestamp)
        }        
        makePlots(data);
        $("#load-status").fadeOut(555);
        reloads += 1;
    }); 
    setTimeout("loadData()", data_reload);
}
