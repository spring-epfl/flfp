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

    _a = a.lower()
    _b = b.lower()

    if _a.replace(" filter", "") == _b.replace(" filter", ""):
        return True

    # only if the only difference between them is the word "list"
    if _a.replace(" list", "") == _b.replace(" list", ""):
        return True

    return False


def remove_default_lists(webdriver, extension_id: str):
    """Remove all default filter lists from the extension settings"""
    webdriver.get(f"chrome-extension://{extension_id}/pages/options.html#filters")

    webdriver.execute_script(
        """
        document.querySelectorAll(".checkbox__in").forEach(el=> {
            if (el.checked) {
                el.click();
            }
        })
    """
    )


def activate_all(webdriver):
    """Activate all filter lists in the current group"""
    webdriver.execute_script(
        """
        document.querySelectorAll(".checkbox__in").forEach(el=> {
            if (!el.checked) {
                el.click();
            }
        })
    """
    )

    time.sleep(3)

    all_checked = webdriver.execute_script(
        """
        // reload the page to make sure the changes are reflected
        // location.reload();
        
        let all_checked = true;
        document.querySelectorAll(".checkbox__in").forEach(el=> {
            if (!el.checked) {
                all_checked = false;
            }
        })
        return all_checked;
        """
    )

    return all_checked


def get_activations_in_current_group(webdriver):
    """Get the activation status of all filter lists in the current group"""

    return webdriver.execute_script(
        """
        let activations = {};
        document.querySelectorAll(".setting-checkbox").forEach(el=> {
            let title = el.querySelector(".filter__title-in").textContent;
            let checked = el.querySelector("input").checked;
            activations[title] = checked;
        })
        return activations;
        """
    )


def activate_by_names_in_group(webdriver, titles: list[str]):
    """Activate filter lists by name in the current group"""

    script_template = """
    
    let titles = arguments[0];
    
    document.querySelectorAll(".setting-checkbox").forEach(el=> {
        let title = el.querySelector(".filter__title-in").textContent;
        let checked = el.querySelector("input").checked;
        
        if (!checked && titles.includes(title)) {
            el.querySelector(".checkbox__label").click();
        }
        
        if (checked && !titles.includes(title)) {
            el.querySelector(".checkbox__label").click();
        }
    })
    """

    webdriver.execute_script(script_template, titles)

    time.sleep(3)

    accept_modal(webdriver)

    time.sleep(2)

    current_activations = get_activations_in_current_group(webdriver)

    for key in current_activations:

        if current_activations[key] != (key in titles):
            print("FAILED TO ACTIVATE", key)
            return False

    return True


def verify_selected(webdriver, extension_id: str, names: list[str] | bool):
    """Verify that the filter lists are selected as expected"""

    names_lower_case = (
        [name.lower() for name in names] if isinstance(names, list) else []
    )
    unmentioned = []
    if isinstance(names, bool) and names:
        inconsistencies = {}
    else:
        inconsistencies = {name: "NOT FOUND" for name in names_lower_case}

    time.sleep(4)

    for group in range(1, 8):
        webdriver.get(
            f"chrome-extension://{extension_id}/pages/options.html#filters?group={group}"
        )
        wait_until_loaded(webdriver, 10)

        current_activations = get_activations_in_current_group(webdriver)

        for title in current_activations:
            checked = current_activations[title]

            found = False
            for key in names_lower_case:
                if keys_match(title, key):
                    inconsistencies[key] = not checked
                    found = True
                    break

            if not found:
                inconsistencies[title.lower()] = checked
                unmentioned.append(title.lower())

    if isinstance(names, list) and any(inconsistencies.values()):

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
                and not any(keys_match(key, name) for key in names_lower_case)
            ],
        )
        print("UNMENTIONED", unmentioned)
        raise ValueError("Inconsistencies found")

    if isinstance(names, bool) and names and not all(inconsistencies.values()):
        print("REAL ACTIVATION STATE", inconsistencies)
        raise ValueError("Inconsistencies found")


def accept_modal(webdriver):
    """Accept the modal that appears after changing the filter list settings"""

    # modal can be of class modal or ReactModalPortal
    modal = webdriver.find_elements(By.CLASS_NAME, "modal")

    if not modal:
        modal = webdriver.find_elements(By.CLASS_NAME, "ReactModalPortal")

    if modal:
        print(f"CONFIRMATION MODAL APPEARED")
        modal = modal[0]
        accept_button = webdriver.find_elements(
            By.CLASS_NAME, ".ReactModalPortal button--green"
        )

        if accept_button:
            try:
                accept_button[0].click()
            except Exception as e:
                print("Failed to accept modal", e)
                raise e

        else:
            print("No accept button found")
            raise ValueError("No accept button found")

        time.sleep(1)


def select_by_names(webdriver, extension_id: str, names: list[str] | bool):
    """Select filter lists by name"""

    if not names:
        time.sleep(15)
        return

    select_all = isinstance(names, bool) and names

    names_lower_case = [name.lower() for name in names] if not select_all else []

    for group in range(1, 8):
        webdriver.get(
            f"chrome-extension://{extension_id}/pages/options.html#filters?group={group}"
        )

        time.sleep(3)
        wait_until_loaded(webdriver, 10)

        # activate the group first
        title_container_setting_box = webdriver.find_element(
            By.CSS_SELECTOR, ".title__container .setting__container"
        )

        checked = webdriver.execute_script(
            'return arguments[0].querySelector("input").checked;',
            title_container_setting_box,
        )

        print(f"GROUP {group} IS", "ACTIVE" if checked else "INACTIVE")

        if not checked:
            print("ACTIVATING GROUP")
            title_container_setting_box.find_element(
                By.CLASS_NAME, "checkbox__label"
            ).click()

            time.sleep(5)
            # check if a modal for confirmation is displayed
            accept_modal(webdriver)

        if select_all:
            print("SELECTING ALL")
            activated = activate_all(webdriver)
            if activated:
                print("ALL SELECTED")
                continue
            else:
                print(
                    "FAILED TO SELECT ALL, FALLING BACK TO ACTIVATING BY NAME IN BATCH"
                )

        current_activations = get_activations_in_current_group(webdriver)

        titles_to_activate = []

        for title in current_activations:

            if select_all or (
                isinstance(names, list)
                and any(keys_match(title, name) for name in names_lower_case)
            ):
                titles_to_activate.append(title)

        if titles_to_activate:
            print("ACTIVATING IN BATCH", titles_to_activate)
            activated = activate_by_names_in_group(webdriver, titles_to_activate)

            if not activated:
                print(
                    "FAILED TO ACTIVATE IN BATCH, FALLING BACK TO INDIVIDUAL SELECTION"
                )
            else:
                continue

        # fall back to individual selection
        for elem in webdriver.find_elements(By.CLASS_NAME, "setting-checkbox"):
            title = elem.find_element(By.CLASS_NAME, "filter__title-in").text
            checked = webdriver.execute_script(
                'return arguments[0].querySelector("input").checked;', elem
            )

            if select_all or (
                isinstance(names, list)
                and any(keys_match(title, name) for name in names_lower_case)
            ):
                if not checked:

                    if keys_match(title, "adguard popups filter"):
                        print("CHECKING", title)
                    elem.find_element(By.CLASS_NAME, "checkbox__label").click()

                    time.sleep(2)
                    # check if a modal for confirmation is displayed

                    accept_modal(webdriver)

                else:
                    if keys_match(title, "adguard popups filter"):
                        print("ALREADY CHECKED", title)

            else:
                if checked:
                    if keys_match(title, "adguard popups filter"):
                        print("UNCHECKING", title)
                    elem.find_element(By.CLASS_NAME, "checkbox__label").click()
                else:
                    if keys_match(title, "adguard popups filter"):
                        print("ALREADY UNCHECKED", title)

    verify_selected(webdriver, extension_id, names)


def setup(driver, extension_id, filterlists: list | str | None = None):
    """Setup the extension with the specified filter lists"""

    if filterlists is None:
        print("No filterlists specified, using default")
        return

    if isinstance(filterlists, str) and filterlists == "all":
        select_by_names(driver, extension_id, True)
        return

    if isinstance(filterlists, list):
        select_by_names(driver, extension_id, filterlists)
        return

    raise ValueError("Invalid filterlists argument")
