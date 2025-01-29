// embed this in https://adguard.com/kb/general/ad-filtering/adguard-filters/

(() => {
  let out_list = [];

  document.querySelectorAll("ul a").forEach((a_tag) => {
    if (a_tag.innerText.includes("View rules")) {
      out_list.push({
        name: a_tag.parentElement.querySelector("strong").innerText,
        url: a_tag.href,
      });
    }
  });

  let yaml_str = out_list
    .map((item) => {
      return `- name: ${item.name}
    url: ${item.url}`;
    })
    .join("\n");

  return yaml_str;
})();
