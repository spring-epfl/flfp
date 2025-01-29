import time
from filterlists.common import wait_until_loaded
from selenium.webdriver.common.by import By


def keys_match(a: str, b: str):
    """check if two filter list names are the same, ignoring aliases

    Args:
        a (str): name of 1st filter list
        b (str): name of 2nd filter list

    Returns:
        bool: True if the two filter list names are the same, False otherwise
    """

    _a = a.lower().replace(" ", "").replace("-", "").replace(chr(8211), "")
    _b = b.lower().replace(" ", "").replace("-", "").replace(chr(8211), "")

    return _a == _b


def interact_for_default(webdriver):
    """Interact with the page to set the default filter lists"""

    # just activate some leaf that should not be activated by default then deactivate it

    current_activations = get_current_activations(webdriver)

    if current_activations["adguard-social"]["checked"]:
        return False

    webdriver.execute_script(
        """
        let elem = document.querySelector(".listEntry[data-key='adguard-social']");
        
        elem.querySelector(".detailbar label").click();
        """
    )

    time.sleep(3)

    apply_all_btn = webdriver.find_element(By.ID, "buttonApply")

    apply_all_btn.click()

    time.sleep(3)

    webdriver.execute_script(
        """
        let elem = document.querySelector(".listEntry[data-key='adguard-social']");
        
        elem.querySelector(".detailbar label").click();
        """
    )

    time.sleep(3)

    apply_all_btn = webdriver.find_element(By.ID, "buttonApply")

    apply_all_btn.click()

    time.sleep(4)

    current_activations_after = get_current_activations(webdriver)

    if current_activations_after["adguard-social"]["checked"]:
        raise ValueError("Failed to deactivate adguard-social")

    return True


def activate_all(webdriver):
    """Activate all filter lists"""
    webdriver.execute_script(
        """
        document.querySelectorAll(".listEntry").forEach(function(elem) {
            let detailbar = elem.querySelector(".detailbar");
            let canCheck = detailbar.querySelector("input") !== null;
            if (!canCheck) return;
            let role = elem.getAttribute("data-role");
            if (role === "leaf") {
                detailbar.querySelector("label").click();
            }
        });
        """
    )

    time.sleep(3)

    apply_all_btn = webdriver.find_element(By.ID, "buttonApply")

    apply_all_btn.click()

    time.sleep(4)

    all_checked = webdriver.execute_script(
        """
        location.reload();
        let all_checked = true;
        document.querySelectorAll(".listEntry[data-key]").forEach(function(elem) {
            
            let detailbar = elem.querySelector(".detailbar");
        
            let canCheck = detailbar.querySelector("input") !== null;
        
            if (!canCheck) return;
            
            let role = elem.getAttribute("data-role");
            
            // only click on leafs and the parent will be automatically checked
            if (role !== "leaf") return;
            
            let checked = detailbar.querySelector("input")?.checked && detailbar.querySelector(".input.checkbox.partial") === null;
            
            if (!checked) {
                all_checked = false;
            }
        });
        return all_checked;
        """
    )

    return all_checked


def activate_by_names(webdriver, names: list[str]):
    """Activate filter lists by their names"""

    script_template = """
    let titles = arguments[0];

    let leafs_that_should_not_uncheck = []; 
    
    document.querySelectorAll(".listEntry").forEach(async function(elem) {
        
        let detailbar = elem.querySelector(".detailbar");
        
        let canCheck = detailbar.querySelector("input") !== null;
        
        if (!canCheck) return;
        
        let role = elem.getAttribute("data-role");
        
        let checked = detailbar.querySelector("input")?.checked && detailbar.querySelector(".input.checkbox.partial") === null;
        
        let title = elem.getAttribute("data-key");
        
        if (title === undefined) {
            return;
        }

        if (titles.includes(title) && role !== "leaf"){
            // add leafs that should not uncheck

                elem.querySelectorAll(".listEntry[data-key]").forEach( child => leafs_that_should_not_uncheck.push(child.getAttribute("data-key")));
        }
    
        if (!checked && titles.includes(title)) {
            detailbar.querySelector("label").click();
            
            if (role !== "leaf") {
                checked = detailbar.querySelector("input")?.checked && detailbar.querySelector(".input.checkbox.partial") === null;

                
                while (!checked) {
                    detailbar.querySelector("label").click();
                    
                    // sleep for a while
                    await new Promise(r => setTimeout(r, 1000));
                    
                    checked = detailbar.querySelector("input")?.checked && detailbar.querySelector(".input.checkbox.partial") === null;
                }
            }
        }
        
        if (checked && !titles.includes(title) && !leafs_that_should_not_uncheck.includes(title)){
            if (role === "leaf") {
                detailbar.querySelector("label").click();
            }
        }
    });
    """

    webdriver.execute_script(script_template, names)

    time.sleep(4)

    current_activations = get_current_activations(webdriver)

    leafs_of_names = set()

    for title in current_activations:

        if title in names:
            leafs_of_names.update(current_activations[title]["leafs"])

    for title in current_activations:
        if current_activations[title]["checked"] != (
            title in names or title in leafs_of_names
        ):

            if current_activations[title]["checked"]:
                print("FAILED TO DEACTIVATE", title)
            else:
                print("FAILED TO ACTIVATE", title)
            return False

    return True


def get_current_activations(webdriver):
    """Get the current activations of the filter lists"""

    activations = webdriver.execute_script(
        """
        let activations = {}
        document.querySelectorAll(".listEntry[data-key]").forEach(function(elem) {
            
            let detailbar = elem.querySelector(".detailbar");
            
            let canCheck = detailbar.querySelector("input") !== null;
        
            if (!canCheck) return;
            
            let role = elem.getAttribute("data-role");
        
            let checked = detailbar.querySelector("input")?.checked && detailbar.querySelector(".input.checkbox.partial") === null;
            let title = elem.getAttribute("data-key");
            
            let leafs = [];
            
            if (role !== "leaf") {
                elem.querySelectorAll(".listEntry[data-key]").forEach(function(leaf) {
                    leafs.push(leaf.getAttribute("data-key"));
                });
            }
            
            activations[title] = {'checked': checked, 'role': role, 'leafs': leafs};
        });
        return activations;
        """
    )

    return activations


def verify_selected(webdriver, extension_id, names: list[str] | bool):
    """Verify that the selected filter lists are activated"""

    names_lower_case = (
        [name.lower() for name in names] if not isinstance(names, bool) else []
    )
    unmentioned = []

    if isinstance(names, bool) and names:
        inconsistencies = {}

    else:
        inconsistencies = {name: "NOT FOUND" for name in names_lower_case}

    webdriver.get(f"chrome-extension://{extension_id}/3p-filters.html")

    time.sleep(3)

    wait_until_loaded(webdriver, 20)

    print("VERIFYING SELECTED")

    current_activations = get_current_activations(webdriver)

    leafs_of_names = set()

    # get all leafs of the selected filter lists
    for title in current_activations:
        for name in names_lower_case:
            if keys_match(name, title):
                leafs_of_names.update(current_activations[title]["leafs"])
                break

    # check if the selected filter lists are activated
    for title in current_activations:

        checked = current_activations[title]["checked"]

        found = False

        for key in names_lower_case:

            if keys_match(key, title):
                inconsistencies[key] = not checked
                found = True
                break

        if not found:

            if title in leafs_of_names:
                continue

            inconsistencies[title] = checked
            unmentioned.append(title.lower())

    # check if the selected filter lists are deactivated
    if isinstance(names, list) and any(inconsistencies.values()):

        print("INCONSISTENCIES", inconsistencies)
        print(
            "NOT FOUND",
            [name for name in names_lower_case if inconsistencies[name] == "NOT FOUND"],
        )
        print(
            "SHOULD BE CHECKED",
            [name for name in names_lower_case if inconsistencies[name] == True],
        )
        print(
            "SHOULD BE UNCHECKED",
            [
                name
                for name in inconsistencies.keys()
                if inconsistencies[name] == True
                and not any(
                    (keys_match(key, name) or name in leafs_of_names)
                    for key in names_lower_case
                )
            ],
        )
        print("UNMENTIONED", unmentioned)
        raise ValueError("Inconsistencies found")

    if isinstance(names, bool) and names and not all(inconsistencies.values()):
        print("REAL ACTIVATION STATE", inconsistencies)
        raise ValueError("Inconsistencies found")


def select_by_names(webdriver, extension_id: str, names: list[str] | bool):
    """Select filter lists by their names"""

    # open empty page
    webdriver.get("about:blank")

    time.sleep(3)

    # open a new tab
    webdriver.implicitly_wait(10)
    webdriver.get(f"chrome-extension://{extension_id}/3p-filters.html")

    # keep the page open for a while
    time.sleep(3)

    if not names:
        time.sleep(5)
        interact_for_default(webdriver)
        time.sleep(2)
        return

    select_all = isinstance(names, bool) and names
    names_lower_case = [name.lower() for name in names] if not select_all else []

    if select_all:
        print("SELECTING ALL")
        all_checked = activate_all(webdriver)
        if all_checked:
            return verify_selected(webdriver, extension_id, names)
        else:
            print("SELECTING ALL FAILED, FALLING BACK TO SELECTING BY NAMES")

    current_activations = get_current_activations(webdriver)

    titles_to_activate = []

    for title in current_activations:
        if select_all or (
            isinstance(names, list)
            and any(keys_match(title, name) for name in names_lower_case)
        ):
            titles_to_activate.append(title)

    print("TITLES TO ACTIVATE", titles_to_activate)
    activated = True
    if titles_to_activate:
        print("ACTIVATING IN BATCH", titles_to_activate)
        activated = activate_by_names(webdriver, titles_to_activate)

        if not activated:
            print("ACTIVATING IN BATCH FAILED, FALLING BACK TO SELECTING INDIVIDUALLY")

    # FALLBACK

    if not activated:

        changed_anything = False

        for elem in webdriver.find_elements(By.CSS_SELECTOR, ".listEntry"):
            title = elem.get_attribute("data-key")
            if not title:
                continue

            checked = webdriver.execute_script(
                'return arguments[0].querySelector("input").checked;', elem
            )

            if select_all or (
                isinstance(names, list) and title.lower() in names_lower_case
            ):
                if not checked:
                    webdriver.execute_script(
                        'arguments[0].querySelector("label").click();', elem
                    )
                    changed_anything = True

            else:
                if checked:
                    webdriver.execute_script(
                        'arguments[0].querySelector("label").click();', elem
                    )
                    changed_anything = True

        if not changed_anything:
            return

    apply_all_btn = webdriver.find_element(By.ID, "buttonApply")

    apply_all_btn.click()

    time.sleep(4)

    verify_selected(webdriver, extension_id, names)


def setup(driver, extension_id, filterlists: list | str | None = None):
    """Setup uBlock Origin with the specified filter lists"""

    if filterlists is None:
        print("No filterlists specified, using default")
        select_by_names(driver, extension_id, None)
        return

    if isinstance(filterlists, str) and filterlists == "all":
        select_by_names(driver, extension_id, True)
        return

    if isinstance(filterlists, list):
        select_by_names(driver, extension_id, filterlists)
        return

    raise ValueError("Invalid filterlists argument")
