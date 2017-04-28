<!DOCTYPE html>
<html lang="en">
% include('~head.tpl', title='Nick Balboni | The Man, The Legend', description='Welcome to nickbalboni.com!')
  <body class="main nick">
    % include('~header.tpl', page="resume")
    <main class="resume">
      <!--embed src="resume.pdf" type='application/pdf'-->
      <iframe src="http://docs.google.com/gview?url=http://nickbalboni.com/resume.pdf&embedded=true" frameborder="0"></iframe>
    </main>
    % include('~footer.tpl')
  </body>
</html>
