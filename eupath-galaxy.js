// Title content
document.getElementById("eupath-title").innerHTML = "" +
        "Welcome to the EuPathDB Galaxy Site";

// Subtitle content
document.getElementById("eupath-subtitle").innerHTML = "" +
        "A free, interactive, web-based platform for large-scale data analysis";

// Introductory paragraph content
document.getElementById("eupath-intro").innerHTML = "" +
                "<ol><li>Start analyzing your data now.  All EuPathDB genomes are pre-loaded.  Pre-configured workflows are available.</li>" +
                "<li>Perform large-scale data analysis with no prior programming or bioinformatics experience.</li>" +
                "<li>Create custom workflows using an interactive workflow editor. <a target='_blank'  href='https://wiki.galaxyproject.org/Learn/AdvancedWorkflow'>Learn how</a></li> " +
                "<li>Visualize your results (BigWig) in GBrowse. </li>" +
                "<li>Keep data private, or share it with colleagues or the community. </li></ol>" +
                "<i>To learn more about Galaxy check out public Galaxy resources:  </i><a target='_blank' href='https://wiki.galaxyproject.org/Learn'>Learn Galaxy</a>";


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
	"<p title=\"click to run the workflow\"><a id='workflow1' href='javascript:void(0)' onClick='import_and_run_workflow(\"95c953aafa7b040f\")'>EuPathDB Workflow for Illumina paired-end RNA-seq, single replicate</a><br>" +
        "Profile a transcriptome and analyze differential gene expression in <i>Aspergillus nidulans</i>.<br>Tools: FastQC, GSNAP, CuffLinks, CuffDiff.</p>" +
        "<p title=\"not ready\"><a id='workflow1' href='javascript:void(0)'>EuPathDB Workflow for Illumina paired-end RNA-seq, biological replicates</a><br>" +
        "Profile a transcriptome and analyze differential gene expression in <i>Aspergillus nidulans</i>.<br>Tools: FastQC, TopHatforIllumina, CuffLinks, CuffDiff.<br></p>";


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




