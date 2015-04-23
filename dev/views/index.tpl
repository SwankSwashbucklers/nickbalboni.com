<!DOCTYPE html>
<html lang="en">
% include('~head.tpl', title='Nick Balboni | The Man, The Legend', description='Welcome to nickbalboni.com!')
% test = request.environ.copy()
    <body>
    	<ul id="list">
    	% for key, value in test.items():
    		<li>
    			<h1 style="font-size: 12px;">{{key}}:  <span style="font-weight: normal;">{{value}}</span></h1>
    		</li>
    	% end
    	</ul>
    	<script type="text/javascript">
    		
    	</script>
    </body>
</html>