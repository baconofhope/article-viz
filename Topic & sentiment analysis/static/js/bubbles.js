const d3 = require('d3');

d3.select("#sentiment-bubbles").selectAll("svg").remove();

var data = d3.json("/get-data");

var w = 800;
var h = 700;
var margin = 80;

var rScale = d3.scaleLinear()
.domain(d3.extent(data, d => d.frequency)).nice()
.range([10, 100])

var yScale = d3.scaleLinear()
.domain(d3.extent(data, d => d.avg_sentiment)).nice()
.range([h-margin, margin])

var color = d3.scaleLinear()
        .domain([-0.7, 0, 0.7])
        .range(["#FF8383", "#FFFFFF", "#7097FF"])
        .interpolate(d3.interpolateRgb.gamma(2.2))

const svg = d3.select("#sentiment-bubbles").append("svg")
.attr("viewBox", [0, 0, w, h])
.attr("font-size", 10)
.attr("font-family", "sans-serif")
.attr("text-anchor", "middle");

const nodes = data;

let simulation = d3.forceSimulation();

simulation = simulation
    .force("collide", d3.forceCollide(d => rScale(d.frequency)+10).iterations(12))
    .force("charge", d3.forceManyBody(50))
    .velocityDecay(0.75)
    .alphaDecay(0.006);

simulation.force('y', d3.forceY().y(function(d) {
    return yScale(d.avg_sentiment);
}))
    .force('x', d3.forceX().x(function(d) {
    return w/2;
}))

simulation
    .nodes(data);

const node = svg.selectAll("g")
.data(nodes)
.join("g")
.attr("class", "node")
.on("mouseover", mover)
.on("mouseout", mout);

node.append("circle")
    .attr("r", d => rScale(d.frequency))
    .attr("fill-opacity", 0.9)
    .attr("fill", d => color(d.avg_sentiment))
    .style("stroke", "#E1E0E2");

node.append("text")
    .selectAll("tspan")
    .data(d => d.name.split(/(?=[A-Z][^A-Z])/g))
    .join("tspan")
    .attr("x", 0)
    .attr("y", (d, i, nodes) => `${i - nodes.length / 2 + 0.8}em`)
    .text(d => d);

simulation.on("tick", () => {
    node
        .attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });
});

function mover(d) {
    svg.selectAll("*").transition()
        .duration(20)
        .style("fill-opacity", 0.1);

    d3.select(this).selectAll("*")
        .transition()
        .duration(100)		  
        .style("fill-opacity", 1);

    d3.select(this)
        .style("fill-opacity", 1);

}

//Mouseout function
function mout(d) { 
    d3.select(this)
        .datum({selected: false});

    svg.selectAll("*").transition()
        .duration(20)
        .style("fill-opacity", 0.9);

};


