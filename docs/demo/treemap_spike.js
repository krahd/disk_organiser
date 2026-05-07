(function () {
  // Sample hierarchical data (bytes)
  const sample = {
    name: "root",
    children: [
      {
        name: "Users",
        children: [
          { name: "Photos", value: 12000000000 },
          { name: "Videos", value: 54000000000 },
          { name: "Documents", value: 8000000000 }
        ]
      },
      { name: "Applications", value: 8000000000 },
      { name: "System", value: 16000000000 },
      { name: "Backups", value: 4000000000 }
    ]
  };

  function render(data) {
    const container = d3.select("#treemap");
    container.html("");
    const width = Math.min(window.innerWidth - 40, 1100);
    const height = 600;
    const format = d3.format(",d");
    const color = d3.scaleOrdinal(d3.schemeCategory10);

    const root = d3
      .hierarchy(data)
      .sum((d) => d.value || 0)
      .sort((a, b) => b.value - a.value);

    d3.treemap().size([width, height]).paddingInner(1)(root);

    const svg = container.append("svg").attr("width", width).attr("height", height);

    const cell = svg
      .selectAll("g")
      .data(root.descendants().filter((d) => d.depth > 0))
      .join("g")
      .attr("transform", (d) => `translate(${d.x0},${d.y0})`)
      .style("cursor", "pointer")
      .on("click", (event, d) => showDetails(d));

    cell
      .append("rect")
      .attr("width", (d) => Math.max(0, d.x1 - d.x0))
      .attr("height", (d) => Math.max(0, d.y1 - d.y0))
      .attr("fill", (d) => color(d.depth));

    cell
      .append("text")
      .attr("x", 4)
      .attr("y", 14)
      .text((d) => (d.data.name ? d.data.name + (d.value ? ` (${format(d.value)} B)` : "") : ""))
      .attr("pointer-events", "none")
      .style("font-size", "12px")
      .style("fill", "#fff");

    const tooltip = d3.select("body").append("div").attr("class", "tooltip");

    cell
      .on("mouseover", function (event, d) {
        tooltip
          .style("display", "block")
          .html(`<strong>${d.data.name}</strong><br/>${format(d.value)} bytes`);
      })
      .on("mousemove", function (event) {
        tooltip.style("left", event.pageX + 10 + "px").style("top", event.pageY + 10 + "px");
      })
      .on("mouseout", function () {
        tooltip.style("display", "none");
      });
  }

  function showDetails(node) {
    const path = node.ancestors().reverse().map((n) => n.data.name).join("/");
    const fmt = d3.format(",d");
    // Lightweight detail view for spike — could be a modal
    alert(`Path: ${path}\nSize: ${fmt(node.value)} bytes\nDepth: ${node.depth}`);
  }

  document.getElementById("reset").addEventListener("click", () => render(sample));
  window.addEventListener("resize", () => render(sample));

  // initial render
  render(sample);
})();
