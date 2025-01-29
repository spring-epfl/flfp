import { RuleParser } from "@adguard/agtree";
import fs from "fs";

function parseFilterlist(filepath) {
  // load lines from file and parse them one by one
  console.log("START_OUTPUT")
//   return 
  fs.readFileSync(filepath, "utf-8")
    .split("\n")
    .forEach((line, index) => {
      // parse line
      _parseFilterRule(line, index);
    }
  );
    console.log("END_OUTPUT")
}

function _parseFilterRule(line, index=0) {
  try {
    const rule = RuleParser.parse(line);
    // if rule is not null, print it
    if (rule) {
      console.log(JSON.stringify(rule));
    }
  } catch (e) {
    console.log(
      JSON.stringify({
        category: "ParserError",
        type: null,
        syntax: null,
        marker: null,
        text: e.message,
        loc: {
          start: { offset: 0, line: index, column: 1 },
          end: { offset: 0, line: index, column: 1 },
        },
      })
    );
  }
}

function parseFilterRules(rules) {
  console.log("START_OUTPUT");

  rules.forEach((rule, index) => {
    _parseFilterRule(rule, index);
  });

  console.log("END_OUTPUT");


}

function parseFilterRule(rule) {
  console.log("START_OUTPUT");

  _parseFilterRule(rule);

  console.log("END_OUTPUT");

}

const action = process.argv[2];
const arg = process.argv[3];


if (action === "file"){
  parseFilterlist(arg);
}
else if (action === "rules"){
  parseFilterRules(JSON.parse(arg));
}
else if (action === "rule"){
  parseFilterRule(JSON.parse(arg));
}
else {
  throw new Error("Unknown action: " + action);
}

