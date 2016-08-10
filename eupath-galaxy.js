// Title content
document.getElementById("eupath-title").innerHTML = "" +
        "Welcome to the EuPathDB Galaxy Site!";

// Subtitle content
document.getElementById("eupath-subtitle").innerHTML = "" +
        "Free, interactive, web-based platform for large-scale data analysis";

// Introductory paragraph content
document.getElementById("eupath-intro").innerHTML = "" +
		"EuPathDB Galaxy workspaces require no prior knowledge of programming or bioinformatics experience." +
		" This Galaxy instance integrates bioinformatics algorithms and tools into an easy to use interactive platform" +
		" that offers pre-loaded annotated genomes and workflows to help you perform large-scale data analysis. You can also" +
		" upload your own data, compose and run custom workflows, retrieve results and share your workflows and data" +
		" analyses with colleagues.";

// Links content
/*
document.getElementById("eupath-links").innerHTML = "" +
        "<li><a href='#'>Link A</a></li>" +
		"<li><a href='#'>Link B</a></li>" +
		"<li><a href='#'>Link C</a></li>";
*/

// Workflows content
// Warning insure ids inside onClick events are correct for galaxy site to which this is deployed. 
document.getElementById("eupath-workflows").innerHTML = "" +
		"<tr><td class=\"notice_table_name\"><a id='workflow1' href='javascript:void(0)' onClick='import_and_run_workflow(\"f368422bc832315d\")'>Workflow 1</a></td></tr>" +
        "<tr><td>Workflow 1 Description</td></tr>";

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




