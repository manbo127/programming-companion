const Markdown = {
  escape(value) {
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
    return String(value ?? "").replace(/[&<>"']/g, char => map[char]);
  },

  inline(value) {
    return value
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>");
  },

  render(value) {
    const codeBlocks = [];
    let source = this.escape(value).replace(/```(?:\w+)?\s*\n?([\s\S]*?)```/g, (_, code) => {
      const token = `@@CODE_BLOCK_${codeBlocks.length}@@`;
      codeBlocks.push(`<pre class="code-block"><code>${code.trim()}</code></pre>`);
      return `\n\n${token}\n\n`;
    });

    const blocks = source.split(/\n{2,}/).map(block => block.trim()).filter(Boolean);
    const html = blocks.map(block => {
      const codeMatch = block.match(/^@@CODE_BLOCK_(\d+)@@$/);
      if (codeMatch) return codeBlocks[Number(codeMatch[1])] || "";

      const lines = block.split("\n");
      if (lines.every(line => /^[-*]\s+/.test(line))) {
        return `<ul>${lines.map(line => `<li>${this.inline(line.replace(/^[-*]\s+/, ""))}</li>`).join("")}</ul>`;
      }
      if (lines.every(line => /^\d+[.)]\s+/.test(line))) {
        return `<ol>${lines.map(line => `<li>${this.inline(line.replace(/^\d+[.)]\s+/, ""))}</li>`).join("")}</ol>`;
      }
      if (/^###\s+/.test(block)) return `<h3>${this.inline(block.replace(/^###\s+/, ""))}</h3>`;
      if (/^##\s+/.test(block)) return `<h2>${this.inline(block.replace(/^##\s+/, ""))}</h2>`;
      if (/^---$/.test(block)) return "<hr>";
      return `<p>${this.inline(block).replace(/\n/g, "<br>")}</p>`;
    }).join("");

    return html || "<p></p>";
  },
};
