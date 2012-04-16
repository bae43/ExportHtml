import sublime
import sublime_plugin
import hashlib


def clean_invalid_regions(view, annotations):
    deletions = 0
    for x in range(0, int(annotations["count"])):
        key_name = "html_annotation_%d" % x
        regions = view.get_regions(key_name)
        if len(regions) and not regions[0].empty():
            annotations["annotations"]["html_annotation_%d" % x]["region"] = [regions[0].begin(), regions[0].end()]
            if deletions:
                new_key = "html_annotation_%d" % (x - deletions)
                annotations["annotations"][new_key] = annotations["annotations"][key_name]
                del annotations["annotations"][key_name]
                new_region = annotations["annotations"][new_key]["region"]
                view.erase_regions(key_name)
                view.add_regions(
                    new_key,
                    [sublime.Region(new_region[0], new_region[1])],
                    "text",
                    ""
                )
        else:
            del annotations["annotations"]["html_annotation_%d" % x]
            annotations["count"] -= 1
            deletions += 1
            if len(regions):
                view.erase_regions(key_name)

    view.settings().set("annotation_comments", annotations)


def get_annotations(view):
    annotations = view.settings().get("annotation_comments", {"count": 0, "annotations": {}})
    clean_invalid_regions(view, annotations)
    return annotations


def clear_annotations(view):
    annotations = view.settings().get("annotation_comments", {"count": 0, "annotations": {}})
    for x in range(0, int(annotations["count"])):
        view.erase_regions("html_annotation_%d" % x)
    view.settings().set("annotation_comments", {"count": 0, "annotations": {}})


def delete_annotations(view):
    annotations = view.settings().get("annotation_comments", {"count": 0, "annotations": {}})
    for sel in view.sel():
        for x in range(0, int(annotations["count"])):
            region = annotations["annotations"]["html_annotation_%d" % x]["region"]
            annotation = sublime.Region(int(region[0]), int(region[1]))
            if annotation.intersects(sel):
                view.erase_regions("html_annotation_%d" % x)
                break
    clean_invalid_regions(view, annotations)


class ClearAnnotationsCommand(sublime_plugin.TextCommand):
    def is_enabled(self):
        return self.view.settings().get("annotation_mode", False)

    def run(self, edit):
        clear_annotations(self.view)


class DeleteAnnotationsCommand(sublime_plugin.TextCommand):
    def is_enabled(self):
        return self.view.settings().get("annotation_mode", False)

    def run(self, edit):
        delete_annotations(self.view)


class ToggleAnnotationHtmlModeCommand(sublime_plugin.TextCommand):
    def is_enabled(self):
        return not self.view.settings().get('is_widget')

    def run(self, edit):
        mode = False if self.view.settings().get("annotation_mode", False) else True
        self.view.settings().set("annotation_mode", mode)
        if mode:
            self.view.settings().set("annotation_read_mode", self.view.is_read_only())
            self.view.set_read_only(True)
        else:
            clear_annotations(self.view)
            self.view.set_read_only(self.view.settings().get("annotation_read_mode", False))


class AnnotateHtml(sublime_plugin.TextCommand):
    def subset_annotation_adjust(self):
        subset = None
        comment = ""
        parent = None
        intersect = False
        for k, v in self.annotations["annotations"].items():
            region = sublime.Region(int(v["region"][0]), int(v["region"][1]))
            if region.contains(self.sel):
                subset = region
                comment = v["comment"]
                parent = k
                break
            elif region.intersects(self.sel):
                intersect = True
                break
        if subset != None:
            self.sel = subset
        return comment, parent, intersect

    def add_annotation(self, s, view_id, subset):
        window = sublime.active_window()
        view = window.active_view() if window != None else None
        if s != "" and view != None and view_id == view.id():
            if subset == None:
                idx = self.annotations["count"]
                key_name = ("html_annotation_%d" % idx)
            else:
                key_name = subset

            self.annotations["annotations"][key_name] = {
                "region": [self.sel.begin(), self.sel.end()],
                "hash": str(hashlib.sha1(self.view.substr(self.sel)).hexdigest()),
                "comment": s
            }
            if subset == None:
                self.annotations["count"] += 1
            self.view.settings().set("annotation_comments", self.annotations)

            self.view.add_regions(
                key_name,
                [self.sel],
                "text",
                ""
            )

    def annotation_panel(self, default_comment, subset):
        view_id = self.view.id()
        self.view.window().show_input_panel(
            ("Annotate region (%d, %d)" % (self.sel.begin(), self.sel.end())),
            default_comment,
            lambda x: self.add_annotation(x, view_id=view_id, subset=subset),
            None,
            None
        )

    def is_enabled(self):
        return self.view.settings().get("annotation_mode", False)

    def run(self, edit):
        self.sel = self.view.sel()[0]
        self.annotations = get_annotations(self.view)
        if not self.sel.empty():
            comment, subset, intersects = self.subset_annotation_adjust()
            if not intersects:
                self.annotation_panel(comment, subset)
            else:
                sublime.error_message("Cannot have intersecting annotation regions!")
