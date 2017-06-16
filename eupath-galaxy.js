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
	"<p title=\"Click to run the workflow with your datasets\"><a id='workflow1' href='javascript:void(0)' onClick='import_and_run_workflow(\"cf5cc2be67722f22\")'>EuPathDB Workflow for Illumina paired-end RNA-seq, without replicates</a><br>" +
        "Profile a transcriptome and analyze differential gene expression.<br>Tools: FastQC, Sickle, GSNAP, CuffLinks, CuffDiff.</p>" +
        "<p title=\"Click to run the workflow with your datasets\"><a id='workflow2' href='javascript:void(0)' onClick='import_and_run_workflow(\"ea4c5f681769d783\")'>EuPathDB Workflow for Illumina paired-end RNA-seq, without replicates</a><br>" +
        "Profile a transcriptome and analyze differential gene expression.<br>Tools: FastQC, Trimmomatic, TopHat2, CuffLinks, CuffDiff.</p>" +
        "<p title=\"Click to run the workflow with your datasets\"><a id='workflow3' href='javascript:void(0)' onClick='import_and_run_workflow(\"cd3b9dbf57044ead\")'>EuPathDB Workflow for Illumina paired-end RNA-seq, biological replicates</a><br>" +
        "Profile a transcriptome and analyze differential gene expression.<br>Tools: FastQC, TopHat2, HTseq, DESeq2.<br></p>";
        "<p title=\"Click to run the workflow with your datasets\"><a id='workflow4' href='javascript:void(0)' onClick='import_and_run_workflow(\"c065e7bd4a1680ca\")'>EuPathDB Workflow for Illumina paired-end RNA-seq, biological replicates</a><br>" +
        "Profile a transcriptome and analyze differential gene expression.<br>Tools: FastQC, Trimmomatic, TopHat2, CuffLinks, CuffDiff.<br></p>";
        "<p title=\"Click to run the workflow with your datasets\"><a id='workflow5' href='javascript:void(0)' onClick='import_and_run_workflow(\"i59725c868c65b63f\")'>EuPathDB Workflow for Variant Calling, single-read sequencing</a><br>" +
        "Profile and analyse SNPs.<br>Tools: Bowtie2, FreeBayes, and SnpEff<br></p>";
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




