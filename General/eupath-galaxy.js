// Title content
document.getElementById("eupath-title").innerHTML = "" +
        "Welcome to the VEuPathDB Galaxy Site";

// Subtitle content
document.getElementById("eupath-subtitle").innerHTML = "" +
        "A free, interactive, web-based platform for large-scale data analysis";

// Introductory paragraph content
document.getElementById("eupath-intro").innerHTML = "" +
                "<ol><li>Start analyzing your data now with pre-configured workflows. All VEuPathDB genomes are pre-loaded.</li>" +
                "<li>Perform large-scale data analysis with no prior programming or bioinformatics experience.</li>" +
                "<li>Create custom workflows using an interactive workflow editor. <a target='_blank'  href='https://wiki.galaxyproject.org/Learn/AdvancedWorkflow'>Learn how</a></li> " +
                "<li>Export your results to VEuPathDB, so that you can explore your data with our tools, such as JBrowse and search strategies. See <a href='https://eupathdb.org/assets/GalaxyRNASeqExportTool.pdf' target='_blank'>this tutorial</a>.</li>" +
                "<li>View your results on Galaxy or download results to your computer.</li>" +
                "<li>Keep data private, or share data with colleagues or the community.</li></ol>" +
                "<i>To learn more about Galaxy, visit the </i><a target='_blank' href='https://wiki.galaxyproject.org/Learn'>public Galaxy resources</a>.";


// Links content
/*
document.getElementById("eupath-links").innerHTML = "" +
        "<li><a href='#'>Link A</a></li>" +
                "<li><a href='#'>Link B</a></li>" +
                "<li><a href='#'>Link C</a></li>";
*/

        
/**
 * A series of ajax calls to import a published workflow (if not already imported) and get its id,
 * followed by a redirect to run the imported workflow
 * @param id - the published (shared) workflow to import
 */
import_and_run_workflow = function(id) {
  var base_url = location.protocol + "//" + location.host;
  var import_id = "";
  // First ajax call to get the name of the workflow to import
  jQuery.get(base_url + "/api/workflows/" + id, function (result) {
    var name = result.name;
    // Second ajax call to determine if the workflow was already imported.
    jQuery.get(base_url + "/api/workflows", function (results) {
      for(i = 0; i < results.length; i++) {
        if(results[i].name.startsWith("imported: ") && results[i].name.endsWith(name)) {
          import_id = results[i].id;
          break;
        }
      }
      // If no import exists issue a third ajax call to actually import the workflow
      if(import_id.length == 0) {
        jQuery.post(base_url + "/api/workflows/import",{"workflow_id":id},function(id) {
          // Fourth ajax call to find the newly imported workflow based upon the 'imported: '
          // key phrase, followed by the name of the original workflow
          jQuery.get(base_url + "/api/workflows", function (results) {
            for(i = 0; i < results.length; i++) {
              if(results[i].name.startsWith("imported: ") && results[i].name.endsWith(name)) {
                import_id = results[i].id;
                break;
              }
            }  
            // If the id of the imported workflow is (hopefully always) found, redirect to the
            // url that runs that workflow.
            if(import_id.length > 0) {
              location.href = "/workflow/run?id=" + import_id;
            }
          });
        });
      }
      // Import already exists.  Just run it.
      else {
        location.href = "/workflow/run?id=" + import_id;
      }    
    });
  });  
}


